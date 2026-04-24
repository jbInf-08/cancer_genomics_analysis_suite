#!/usr/bin/env python3
"""
Token Handler

This module provides token management capabilities for OAuth2 authentication
in the cancer genomics analysis suite.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import secrets
import hashlib

try:
    from jose import jwt, JWTError
    from jose.exceptions import ExpiredSignatureError, JWTClaimsError
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logging.warning("JWT libraries not available. Install python-jose package.")

logger = logging.getLogger(__name__)


class TokenHandler:
    """
    Token handler for OAuth2 authentication.
    
    Provides functionality to:
    - Generate and validate JWT tokens
    - Manage token storage and retrieval
    - Handle token refresh and expiration
    - Implement token security features
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize token handler.
        
        Args:
            config: Token configuration
        """
        if not JWT_AVAILABLE:
            raise ImportError("JWT libraries not available. Install python-jose package.")
        
        self.config = config or {}
        
        # JWT settings
        self.secret_key = self.config.get("secret_key", secrets.token_urlsafe(32))
        self.algorithm = self.config.get("algorithm", "HS256")
        self.access_token_expiry = self.config.get("access_token_expiry", 3600)  # 1 hour
        self.refresh_token_expiry = self.config.get("refresh_token_expiry", 86400 * 7)  # 7 days
        
        # Token storage
        self.token_storage = {}
        self.refresh_tokens = {}
        
        # Security settings
        self.token_blacklist = set()
        self.max_tokens_per_user = self.config.get("max_tokens_per_user", 5)
        self.token_rotation_enabled = self.config.get("token_rotation", True)
        
        # Statistics
        self.token_stats = {
            "tokens_issued": 0,
            "tokens_refreshed": 0,
            "tokens_revoked": 0,
            "tokens_expired": 0
        }
    
    def init_app(self, app):
        """
        Initialize token handler with Flask app.
        
        Args:
            app: Flask application instance
        """
        # Update secret key from app config if available
        if hasattr(app, 'config') and app.config.get('SECRET_KEY'):
            self.secret_key = app.config['SECRET_KEY']
        
        logger.info("Token handler initialized with Flask app")
    
    def generate_access_token(
        self,
        user_id: str,
        username: str,
        roles: List[str] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate access token for user.
        
        Args:
            user_id: User ID
            username: Username
            roles: List of user roles
            additional_claims: Additional JWT claims
            
        Returns:
            Access token
        """
        now = datetime.utcnow()
        expiry = now + timedelta(seconds=self.access_token_expiry)
        
        # Create token ID for tracking
        token_id = secrets.token_urlsafe(16)
        
        # Build claims
        claims = {
            "sub": user_id,
            "username": username,
            "roles": roles or [],
            "iat": int(now.timestamp()),
            "exp": int(expiry.timestamp()),
            "jti": token_id,
            "type": "access"
        }
        
        # Add additional claims
        if additional_claims:
            claims.update(additional_claims)
        
        # Generate token
        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        
        # Store token metadata
        self.token_storage[token_id] = {
            "user_id": user_id,
            "username": username,
            "issued_at": now,
            "expires_at": expiry,
            "type": "access",
            "revoked": False
        }
        
        # Update statistics
        self.token_stats["tokens_issued"] += 1
        
        # Clean up old tokens for user
        self._cleanup_user_tokens(user_id)
        
        logger.debug(f"Generated access token for user {username}")
        return token
    
    def generate_refresh_token(
        self,
        user_id: str,
        username: str,
        access_token_id: str
    ) -> str:
        """
        Generate refresh token for user.
        
        Args:
            user_id: User ID
            username: Username
            access_token_id: Associated access token ID
            
        Returns:
            Refresh token
        """
        now = datetime.utcnow()
        expiry = now + timedelta(seconds=self.refresh_token_expiry)
        
        # Create refresh token ID
        refresh_token_id = secrets.token_urlsafe(16)
        
        # Build claims
        claims = {
            "sub": user_id,
            "username": username,
            "iat": int(now.timestamp()),
            "exp": int(expiry.timestamp()),
            "jti": refresh_token_id,
            "type": "refresh",
            "access_token_id": access_token_id
        }
        
        # Generate token
        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        
        # Store refresh token metadata
        self.refresh_tokens[refresh_token_id] = {
            "user_id": user_id,
            "username": username,
            "access_token_id": access_token_id,
            "issued_at": now,
            "expires_at": expiry,
            "revoked": False
        }
        
        logger.debug(f"Generated refresh token for user {username}")
        return token
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Token claims if valid
            
        Raises:
            JWTError: If token is invalid
        """
        try:
            # Decode token
            claims = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is blacklisted
            token_id = claims.get("jti")
            if token_id in self.token_blacklist:
                raise JWTError("Token has been revoked")
            
            # Check token type
            token_type = claims.get("type")
            if token_type == "access":
                # Validate access token
                if token_id not in self.token_storage:
                    raise JWTError("Token not found in storage")
                
                token_metadata = self.token_storage[token_id]
                if token_metadata["revoked"]:
                    raise JWTError("Token has been revoked")
                
                # Update last used time
                token_metadata["last_used"] = datetime.utcnow()
            
            elif token_type == "refresh":
                # Validate refresh token
                if token_id not in self.refresh_tokens:
                    raise JWTError("Refresh token not found in storage")
                
                refresh_metadata = self.refresh_tokens[token_id]
                if refresh_metadata["revoked"]:
                    raise JWTError("Refresh token has been revoked")
            
            return claims
        
        except ExpiredSignatureError:
            self.token_stats["tokens_expired"] += 1
            raise JWTError("Token has expired")
        except JWTClaimsError as e:
            raise JWTError(f"Invalid token claims: {e}")
        except JWTError as e:
            raise JWTError(f"Token validation failed: {e}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dictionary with new access token and refresh token
            
        Raises:
            JWTError: If refresh token is invalid
        """
        try:
            # Validate refresh token
            claims = self.validate_token(refresh_token)
            
            if claims.get("type") != "refresh":
                raise JWTError("Invalid token type for refresh")
            
            refresh_token_id = claims.get("jti")
            user_id = claims.get("sub")
            username = claims.get("username")
            roles = claims.get("roles", [])
            
            # Revoke old tokens if rotation is enabled
            if self.token_rotation_enabled:
                self.revoke_token(refresh_token)
                old_access_token_id = claims.get("access_token_id")
                if old_access_token_id:
                    self.revoke_token_by_id(old_access_token_id)
            
            # Generate new access token
            new_access_token = self.generate_access_token(
                user_id=user_id,
                username=username,
                roles=roles
            )
            
            # Get new access token ID
            new_access_claims = jwt.decode(new_access_token, self.secret_key, algorithms=[self.algorithm])
            new_access_token_id = new_access_claims.get("jti")
            
            # Generate new refresh token
            new_refresh_token = self.generate_refresh_token(
                user_id=user_id,
                username=username,
                access_token_id=new_access_token_id
            )
            
            # Update statistics
            self.token_stats["tokens_refreshed"] += 1
            
            logger.debug(f"Refreshed tokens for user {username}")
            
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "expires_in": self.access_token_expiry
            }
        
        except JWTError as e:
            logger.error(f"Token refresh failed: {e}")
            raise
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token.
        
        Args:
            token: Token to revoke
            
        Returns:
            True if token was revoked
        """
        try:
            # Decode token to get ID
            claims = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            token_id = claims.get("jti")
            token_type = claims.get("type")
            
            if token_type == "access":
                if token_id in self.token_storage:
                    self.token_storage[token_id]["revoked"] = True
                    self.token_blacklist.add(token_id)
                    self.token_stats["tokens_revoked"] += 1
                    return True
            
            elif token_type == "refresh":
                if token_id in self.refresh_tokens:
                    self.refresh_tokens[token_id]["revoked"] = True
                    self.token_blacklist.add(token_id)
                    self.token_stats["tokens_revoked"] += 1
                    return True
            
            return False
        
        except JWTError:
            return False
    
    def revoke_token_by_id(self, token_id: str) -> bool:
        """
        Revoke token by ID.
        
        Args:
            token_id: Token ID to revoke
            
        Returns:
            True if token was revoked
        """
        revoked = False
        
        # Revoke access token
        if token_id in self.token_storage:
            self.token_storage[token_id]["revoked"] = True
            self.token_blacklist.add(token_id)
            revoked = True
        
        # Revoke refresh token
        if token_id in self.refresh_tokens:
            self.refresh_tokens[token_id]["revoked"] = True
            self.token_blacklist.add(token_id)
            revoked = True
        
        if revoked:
            self.token_stats["tokens_revoked"] += 1
        
        return revoked
    
    def revoke_all_user_tokens(self, user_id: str) -> int:
        """
        Revoke all tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of tokens revoked
        """
        revoked_count = 0
        
        # Revoke access tokens
        for token_id, token_metadata in self.token_storage.items():
            if token_metadata["user_id"] == user_id and not token_metadata["revoked"]:
                token_metadata["revoked"] = True
                self.token_blacklist.add(token_id)
                revoked_count += 1
        
        # Revoke refresh tokens
        for token_id, refresh_metadata in self.refresh_tokens.items():
            if refresh_metadata["user_id"] == user_id and not refresh_metadata["revoked"]:
                refresh_metadata["revoked"] = True
                self.token_blacklist.add(token_id)
                revoked_count += 1
        
        if revoked_count > 0:
            self.token_stats["tokens_revoked"] += revoked_count
        
        logger.info(f"Revoked {revoked_count} tokens for user {user_id}")
        return revoked_count
    
    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get token information.
        
        Args:
            token: JWT token
            
        Returns:
            Token information or None if invalid
        """
        try:
            claims = self.validate_token(token)
            token_id = claims.get("jti")
            token_type = claims.get("type")
            
            if token_type == "access" and token_id in self.token_storage:
                metadata = self.token_storage[token_id]
                return {
                    "token_id": token_id,
                    "user_id": metadata["user_id"],
                    "username": metadata["username"],
                    "type": "access",
                    "issued_at": metadata["issued_at"].isoformat(),
                    "expires_at": metadata["expires_at"].isoformat(),
                    "last_used": metadata.get("last_used", metadata["issued_at"]).isoformat(),
                    "revoked": metadata["revoked"]
                }
            
            elif token_type == "refresh" and token_id in self.refresh_tokens:
                metadata = self.refresh_tokens[token_id]
                return {
                    "token_id": token_id,
                    "user_id": metadata["user_id"],
                    "username": metadata["username"],
                    "type": "refresh",
                    "issued_at": metadata["issued_at"].isoformat(),
                    "expires_at": metadata["expires_at"].isoformat(),
                    "access_token_id": metadata["access_token_id"],
                    "revoked": metadata["revoked"]
                }
            
            return None
        
        except JWTError:
            return None
    
    def get_user_tokens(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of token information
        """
        tokens = []
        
        # Get access tokens
        for token_id, metadata in self.token_storage.items():
            if metadata["user_id"] == user_id:
                tokens.append({
                    "token_id": token_id,
                    "type": "access",
                    "issued_at": metadata["issued_at"].isoformat(),
                    "expires_at": metadata["expires_at"].isoformat(),
                    "last_used": metadata.get("last_used", metadata["issued_at"]).isoformat(),
                    "revoked": metadata["revoked"]
                })
        
        # Get refresh tokens
        for token_id, metadata in self.refresh_tokens.items():
            if metadata["user_id"] == user_id:
                tokens.append({
                    "token_id": token_id,
                    "type": "refresh",
                    "issued_at": metadata["issued_at"].isoformat(),
                    "expires_at": metadata["expires_at"].isoformat(),
                    "access_token_id": metadata["access_token_id"],
                    "revoked": metadata["revoked"]
                })
        
        return tokens
    
    def _cleanup_user_tokens(self, user_id: str):
        """Clean up old tokens for a user."""
        # Get all active tokens for user
        user_tokens = []
        
        for token_id, metadata in self.token_storage.items():
            if metadata["user_id"] == user_id and not metadata["revoked"]:
                user_tokens.append((token_id, metadata["issued_at"]))
        
        # Sort by issue time (oldest first)
        user_tokens.sort(key=lambda x: x[1])
        
        # Remove excess tokens
        if len(user_tokens) > self.max_tokens_per_user:
            tokens_to_remove = user_tokens[:-self.max_tokens_per_user]
            for token_id, _ in tokens_to_remove:
                self.revoke_token_by_id(token_id)
    
    def cleanup_expired_tokens(self):
        """Clean up expired tokens."""
        current_time = datetime.utcnow()
        
        # Clean up expired access tokens
        expired_access_tokens = []
        for token_id, metadata in self.token_storage.items():
            if metadata["expires_at"] < current_time:
                expired_access_tokens.append(token_id)
        
        for token_id in expired_access_tokens:
            del self.token_storage[token_id]
            self.token_blacklist.discard(token_id)
        
        # Clean up expired refresh tokens
        expired_refresh_tokens = []
        for token_id, metadata in self.refresh_tokens.items():
            if metadata["expires_at"] < current_time:
                expired_refresh_tokens.append(token_id)
        
        for token_id in expired_refresh_tokens:
            del self.refresh_tokens[token_id]
            self.token_blacklist.discard(token_id)
        
        if expired_access_tokens or expired_refresh_tokens:
            logger.info(f"Cleaned up {len(expired_access_tokens)} expired access tokens and {len(expired_refresh_tokens)} expired refresh tokens")
    
    def get_token_statistics(self) -> Dict[str, Any]:
        """
        Get token statistics.
        
        Returns:
            Dictionary with token statistics
        """
        current_time = datetime.utcnow()
        
        # Count active tokens
        active_access_tokens = sum(
            1 for metadata in self.token_storage.values()
            if not metadata["revoked"] and metadata["expires_at"] > current_time
        )
        
        active_refresh_tokens = sum(
            1 for metadata in self.refresh_tokens.values()
            if not metadata["revoked"] and metadata["expires_at"] > current_time
        )
        
        # Count expired tokens
        expired_access_tokens = sum(
            1 for metadata in self.token_storage.values()
            if metadata["expires_at"] <= current_time
        )
        
        expired_refresh_tokens = sum(
            1 for metadata in self.refresh_tokens.values()
            if metadata["expires_at"] <= current_time
        )
        
        return {
            "active_access_tokens": active_access_tokens,
            "active_refresh_tokens": active_refresh_tokens,
            "expired_access_tokens": expired_access_tokens,
            "expired_refresh_tokens": expired_refresh_tokens,
            "blacklisted_tokens": len(self.token_blacklist),
            "tokens_issued": self.token_stats["tokens_issued"],
            "tokens_refreshed": self.token_stats["tokens_refreshed"],
            "tokens_revoked": self.token_stats["tokens_revoked"],
            "tokens_expired": self.token_stats["tokens_expired"],
            "max_tokens_per_user": self.max_tokens_per_user,
            "token_rotation_enabled": self.token_rotation_enabled
        }
    
    def generate_api_key(
        self,
        user_id: str,
        name: str,
        permissions: List[str] = None,
        expires_in_days: int = 365
    ) -> str:
        """
        Generate API key for user.
        
        Args:
            user_id: User ID
            name: API key name
            permissions: List of permissions
            expires_in_days: Expiration in days
            
        Returns:
            API key
        """
        now = datetime.utcnow()
        expiry = now + timedelta(days=expires_in_days)
        
        # Create API key ID
        api_key_id = secrets.token_urlsafe(16)
        
        # Build claims
        claims = {
            "sub": user_id,
            "name": name,
            "permissions": permissions or [],
            "iat": int(now.timestamp()),
            "exp": int(expiry.timestamp()),
            "jti": api_key_id,
            "type": "api_key"
        }
        
        # Generate API key
        api_key = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        
        # Store API key metadata
        self.token_storage[api_key_id] = {
            "user_id": user_id,
            "name": name,
            "permissions": permissions or [],
            "issued_at": now,
            "expires_at": expiry,
            "type": "api_key",
            "revoked": False
        }
        
        logger.info(f"Generated API key '{name}' for user {user_id}")
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate API key.
        
        Args:
            api_key: API key to validate
            
        Returns:
            API key claims if valid
        """
        try:
            claims = self.validate_token(api_key)
            
            if claims.get("type") != "api_key":
                return None
            
            return claims
        
        except JWTError:
            return None
