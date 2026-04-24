#!/usr/bin/env python3
"""
Test User Model

This script demonstrates the simplified User model
for the Cancer Genomics Analysis Suite.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import create_app, db
from app.auth.models import User
from werkzeug.security import generate_password_hash, check_password_hash

def test_user_model():
    """Test the User model functionality."""
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Create database tables
        db.create_all()
        
        print("👤 Testing User Model")
        print("=" * 50)
        
        # Test 1: Create a basic user
        print("\n1. Creating a basic user...")
        try:
            user = User(
                username="testuser",
                password_hash=generate_password_hash("TestPass123!")
            )
            user.save()
            print(f"   ✅ User created: {user.username} (ID: {user.id})")
            print(f"   Created at: {user.created_at}")
        except Exception as e:
            print(f"   ❌ Error creating user: {e}")
            return
        
        # Test 2: Create a user with additional fields
        print("\n2. Creating a user with additional fields...")
        try:
            enhanced_user = User(
                username="enhanceduser",
                password_hash=generate_password_hash("EnhancedPass123!"),
                email="enhanced@example.com",
                first_name="Enhanced",
                last_name="User",
                is_active=True,
                is_admin=False
            )
            enhanced_user.save()
            print(f"   ✅ Enhanced user created: {enhanced_user.username}")
            print(f"   Email: {enhanced_user.email}")
            print(f"   Name: {enhanced_user.first_name} {enhanced_user.last_name}")
            print(f"   Active: {enhanced_user.is_active}")
            print(f"   Admin: {enhanced_user.is_admin}")
        except Exception as e:
            print(f"   ❌ Error creating enhanced user: {e}")
        
        # Test 3: Test password verification
        print("\n3. Testing password verification...")
        try:
            # Test correct password
            correct_check = check_password_hash(user.password_hash, "TestPass123!")
            print(f"   ✅ Correct password check: {correct_check}")
            
            # Test incorrect password
            incorrect_check = check_password_hash(user.password_hash, "WrongPassword")
            print(f"   ✅ Incorrect password check: {incorrect_check}")
        except Exception as e:
            print(f"   ❌ Error testing password: {e}")
        
        # Test 4: Test user queries
        print("\n4. Testing user queries...")
        try:
            # Find by username
            found_user = User.find_by_username("testuser")
            print(f"   ✅ Find by username: {found_user.username if found_user else 'Not found'}")
            
            # Find by email
            found_by_email = User.find_by_email("enhanced@example.com")
            print(f"   ✅ Find by email: {found_by_email.username if found_by_email else 'Not found'}")
            
            # Find active users
            active_users = User.find_active_users()
            print(f"   ✅ Active users count: {len(active_users)}")
            
            # Find admin users
            admin_users = User.find_admin_users()
            print(f"   ✅ Admin users count: {len(admin_users)}")
        except Exception as e:
            print(f"   ❌ Error testing queries: {e}")
        
        # Test 5: Test user serialization
        print("\n5. Testing user serialization...")
        try:
            user_dict = user.to_dict()
            print(f"   ✅ User dictionary: {user_dict}")
        except Exception as e:
            print(f"   ❌ Error serializing user: {e}")
        
        # Test 6: Test user update
        print("\n6. Testing user update...")
        try:
            user.email = "testuser@example.com"
            user.first_name = "Test"
            user.last_name = "User"
            user.save()
            print(f"   ✅ User updated: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Name: {user.first_name} {user.last_name}")
        except Exception as e:
            print(f"   ❌ Error updating user: {e}")
        
        # Test 7: Test unique constraints
        print("\n7. Testing unique constraints...")
        try:
            duplicate_user = User(
                username="testuser",  # Same username
                password_hash=generate_password_hash("AnotherPass123!")
            )
            duplicate_user.save()
            print("   ❌ Duplicate username should have failed!")
        except Exception as e:
            print(f"   ✅ Duplicate username correctly rejected: {str(e)[:50]}...")
        
        # Test 8: Test user deletion
        print("\n8. Testing user deletion...")
        try:
            # Create a user to delete
            temp_user = User(
                username="tempuser",
                password_hash=generate_password_hash("TempPass123!")
            )
            temp_user.save()
            temp_id = temp_user.id
            print(f"   ✅ Temp user created: {temp_user.username} (ID: {temp_id})")
            
            # Delete the user
            temp_user.delete()
            print(f"   ✅ Temp user deleted")
            
            # Verify deletion
            deleted_user = User.query.get(temp_id)
            print(f"   ✅ User deletion verified: {deleted_user is None}")
        except Exception as e:
            print(f"   ❌ Error testing deletion: {e}")
        
        # Test 9: Display all users
        print("\n9. Current users in database:")
        try:
            all_users = User.query.all()
            for user in all_users:
                print(f"   - {user.username} (ID: {user.id}, Active: {user.is_active})")
        except Exception as e:
            print(f"   ❌ Error listing users: {e}")
        
        print("\n" + "=" * 50)
        print("🎉 User model testing completed!")
        print("\nDatabase schema:")
        print("   - id: Primary key")
        print("   - username: Unique, required")
        print("   - password_hash: Required")
        print("   - created_at: Auto-generated timestamp")
        print("   - email: Optional, unique")
        print("   - first_name: Optional")
        print("   - last_name: Optional")
        print("   - is_active: Boolean, default True")
        print("   - is_admin: Boolean, default False")
        print("   - last_login: Optional timestamp")

def show_sql_schema():
    """Show the SQL schema for the users table."""
    
    print("\n📋 SQL Schema for Users Table:")
    print("=" * 50)
    
    print("""
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email VARCHAR(120) UNIQUE,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_users_admin ON users(is_admin);
""")

def show_usage_examples():
    """Show usage examples for the User model."""
    
    print("\n💡 Usage Examples:")
    print("=" * 50)
    
    print("""
# Create a new user
user = User(
    username="newuser",
    password_hash=generate_password_hash("SecurePass123!")
)
user.save()

# Create user with additional fields
user = User(
    username="fulluser",
    password_hash=generate_password_hash("SecurePass123!"),
    email="user@example.com",
    first_name="John",
    last_name="Doe",
    is_active=True,
    is_admin=False
)
user.save()

# Find user by username
user = User.find_by_username("newuser")

# Find user by email
user = User.find_by_email("user@example.com")

# Get all active users
active_users = User.find_active_users()

# Get all admin users
admin_users = User.find_admin_users()

# Update user
user.email = "newemail@example.com"
user.save()

# Delete user
user.delete()

# Convert to dictionary
user_dict = user.to_dict()

# Verify password
is_valid = check_password_hash(user.password_hash, "password")
""")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--schema":
        show_sql_schema()
    elif len(sys.argv) > 1 and sys.argv[1] == "--examples":
        show_usage_examples()
    else:
        test_user_model()
        show_sql_schema()
        show_usage_examples()
