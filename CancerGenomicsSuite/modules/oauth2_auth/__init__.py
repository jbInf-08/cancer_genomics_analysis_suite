"""
OAuth2 Authentication Module

This module provides OAuth2-based authentication capabilities using Keycloak
and Auth0 for the cancer genomics analysis suite.
"""

from .oauth2_manager import OAuth2Manager
from .keycloak_client import KeycloakClient
from .auth0_client import Auth0Client
from .token_handler import TokenHandler
from .user_manager import UserManager

__all__ = [
    'OAuth2Manager',
    'KeycloakClient',
    'Auth0Client',
    'TokenHandler',
    'UserManager'
]
