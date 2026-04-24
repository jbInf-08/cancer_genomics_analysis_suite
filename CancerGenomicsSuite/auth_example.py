#!/usr/bin/env python3
"""
Authentication System Example

This script demonstrates how to use the authentication system
for the Cancer Genomics Analysis Suite.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import create_app, db
from app.auth import (
    create_user, authenticate_user, validate_password, 
    has_permission, require_permission, require_admin,
    ROLES, PERMISSIONS
)

def main():
    """Main function demonstrating authentication features."""
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Create database tables
        db.create_all()
        
        print("🔐 Cancer Genomics Analysis Suite - Authentication Example")
        print("=" * 60)
        
        # Example 1: Password Validation
        print("\n1. Password Validation Example:")
        passwords = [
            "weak",
            "Weak123",
            "StrongPassword123!",
            "VeryStrongPassword2024!@#"
        ]
        
        for password in passwords:
            result = validate_password(password)
            print(f"   Password: '{password}'")
            print(f"   Valid: {result['valid']}")
            print(f"   Strength: {result['strength']}")
            if result['errors']:
                print(f"   Errors: {', '.join(result['errors'])}")
            print()
        
        # Example 2: User Creation
        print("2. User Creation Example:")
        try:
            # Create an admin user
            admin_user = create_user(
                username="admin",
                email="admin@cancergenomics.com",
                password="AdminPass123!",
                first_name="System",
                last_name="Administrator",
                role="admin"
            )
            print(f"   ✅ Admin user created: {admin_user.username}")
            
            # Create a researcher user
            researcher_user = create_user(
                username="researcher",
                email="researcher@cancergenomics.com",
                password="ResearcherPass123!",
                first_name="Dr. Jane",
                last_name="Smith",
                role="researcher"
            )
            print(f"   ✅ Researcher user created: {researcher_user.username}")
            
            # Create a viewer user
            viewer_user = create_user(
                username="viewer",
                email="viewer@cancergenomics.com",
                password="ViewerPass123!",
                first_name="John",
                last_name="Doe",
                role="viewer"
            )
            print(f"   ✅ Viewer user created: {viewer_user.username}")
            
        except Exception as e:
            print(f"   ❌ Error creating users: {e}")
        
        # Example 3: User Authentication
        print("\n3. User Authentication Example:")
        test_credentials = [
            ("admin", "AdminPass123!"),
            ("researcher", "ResearcherPass123!"),
            ("viewer", "ViewerPass123!"),
            ("admin", "WrongPassword"),
            ("nonexistent", "SomePassword")
        ]
        
        for username, password in test_credentials:
            user = authenticate_user(username, password)
            if user:
                print(f"   ✅ Authentication successful: {user.username} ({'admin' if user.is_admin else 'user'})")
            else:
                print(f"   ❌ Authentication failed: {username}")
        
        # Example 4: Permission Checking
        print("\n4. Permission Checking Example:")
        users = [admin_user, researcher_user, viewer_user]
        permissions = ['read_data', 'write_data', 'run_analysis', 'manage_users']
        
        for user in users:
            print(f"   User: {user.username} ({'admin' if user.is_admin else 'user'})")
            for permission in permissions:
                has_perm = has_permission(user, permission)
                status = "✅" if has_perm else "❌"
                print(f"     {status} {permission}")
            print()
        
        # Example 5: Role Information
        print("5. Available Roles and Permissions:")
        for role_name, role_info in ROLES.items():
            print(f"   Role: {role_name} (Level: {role_info['level']})")
            print(f"     Description: {role_info['description']}")
            print(f"     Permissions: {', '.join(role_info['permissions'])}")
            print()
        
        # Example 6: API Usage
        print("6. API Endpoint Examples:")
        print("   Authentication endpoints:")
        print("     POST /auth/login - User login")
        print("     POST /auth/register - User registration")
        print("     GET /auth/logout - User logout")
        print("     GET /auth/profile - Get user profile")
        print("     PUT /auth/profile/update - Update profile")
        print("     POST /auth/change-password - Change password")
        print()
        print("   Admin endpoints:")
        print("     GET /auth/api/auth/users - List all users")
        print("     GET /auth/api/auth/users/{id} - Get user details")
        print("     PUT /auth/api/auth/users/{id} - Update user")
        print("     DELETE /auth/api/auth/users/{id} - Delete user")
        print()
        print("   Status endpoints:")
        print("     GET /auth/api/auth/status - Authentication status")
        print("     GET /api/status - System status with auth info")
        
        print("\n" + "=" * 60)
        print("🎉 Authentication system example completed!")
        print("\nTo test the authentication system:")
        print("1. Start the Flask app: python run_flask_app.py")
        print("2. Visit: http://localhost:8050")
        print("3. Try the authentication endpoints")
        print("4. Check the API documentation in AUTH_SETUP.md")

if __name__ == "__main__":
    main()
