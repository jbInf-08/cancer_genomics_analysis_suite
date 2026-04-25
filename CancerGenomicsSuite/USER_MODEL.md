# User Model Documentation

This document describes the User model for the Cancer Genomics Analysis Suite authentication system.

## Overview

The User model provides a simple yet flexible user management system with the following core features:

- **Basic Authentication**: Username and password-based authentication
- **Enhanced Fields**: Optional email, name, and status fields
- **Flask-Login Integration**: Compatible with Flask-Login for session management
- **Database Operations**: Save, delete, and query methods
- **Serialization**: JSON conversion for API responses

## Database Schema

### Core Fields (Required)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | Primary Key | Unique user identifier |
| `username` | String(120) | Unique, Not Null | User's login username |
| `password_hash` | String(255) | Not Null | Hashed password |
| `created_at` | DateTime | Default: now() | Account creation timestamp |

### Additional Fields (Optional)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `email` | String(120) | Unique | User's email address |
| `first_name` | String(50) | Nullable | User's first name |
| `last_name` | String(50) | Nullable | User's last name |
| `is_active` | Boolean | Default: True | Account status |
| `is_admin` | Boolean | Default: False | Admin privileges |
| `last_login` | DateTime | Nullable | Last login timestamp |

## SQL Schema

```sql
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
```

## Model Definition

```python
from CancerGenomicsSuite.app import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    # Additional fields for enhanced functionality
    email = db.Column(db.String(120), unique=True, nullable=True)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, nullable=True)
```

## Usage Examples

### Creating Users

#### Basic User Creation
```python
from CancerGenomicsSuite.app.auth.models import User
from werkzeug.security import generate_password_hash

# Create a basic user
user = User(
    username="testuser",
    password_hash=generate_password_hash("SecurePass123!")
)
user.save()
```

#### Enhanced User Creation
```python
# Create a user with additional fields
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
```

### User Queries

#### Find by Username
```python
user = User.find_by_username("testuser")
if user:
    print(f"Found user: {user.username}")
```

#### Find by Email
```python
user = User.find_by_email("user@example.com")
if user:
    print(f"Found user: {user.username}")
```

#### Find Active Users
```python
active_users = User.find_active_users()
print(f"Active users: {len(active_users)}")
```

#### Find Admin Users
```python
admin_users = User.find_admin_users()
print(f"Admin users: {len(admin_users)}")
```

### User Operations

#### Update User
```python
user = User.find_by_username("testuser")
if user:
    user.email = "newemail@example.com"
    user.first_name = "Updated"
    user.save()
```

#### Delete User
```python
user = User.find_by_username("testuser")
if user:
    user.delete()
```

#### Serialize User
```python
user = User.find_by_username("testuser")
if user:
    user_dict = user.to_dict()
    print(user_dict)
```

### Password Management

#### Hash Password
```python
from werkzeug.security import generate_password_hash

password_hash = generate_password_hash("SecurePass123!")
```

#### Verify Password
```python
from werkzeug.security import check_password_hash

user = User.find_by_username("testuser")
if user:
    is_valid = check_password_hash(user.password_hash, "SecurePass123!")
    print(f"Password valid: {is_valid}")
```

## Model Methods

### Instance Methods

#### `save()`
Save the user to the database.
```python
user.save()
```

#### `delete()`
Delete the user from the database.
```python
user.delete()
```

#### `to_dict()`
Convert user to dictionary for JSON serialization.
```python
user_dict = user.to_dict()
```

### Class Methods

#### `find_by_username(username)`
Find a user by username.
```python
user = User.find_by_username("testuser")
```

#### `find_by_email(email)`
Find a user by email address.
```python
user = User.find_by_email("user@example.com")
```

#### `find_active_users()`
Find all active users.
```python
active_users = User.find_active_users()
```

#### `find_admin_users()`
Find all admin users.
```python
admin_users = User.find_admin_users()
```

## Flask-Login Integration

The User model inherits from `UserMixin`, making it compatible with Flask-Login:

```python
from flask_login import login_user, logout_user, current_user

# Login user
user = User.find_by_username("testuser")
if user and check_password_hash(user.password_hash, "password"):
    login_user(user)
    print(f"Logged in: {current_user.username}")

# Logout user
logout_user()
```

## API Integration

### User Registration
```python
from CancerGenomicsSuite.app.auth.models import User
from werkzeug.security import generate_password_hash

def register_user(username, password, email=None):
    # Check if user exists
    if User.find_by_username(username):
        return {"error": "User already exists"}
    
    # Create new user
    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        email=email
    )
    user.save()
    
    return {"message": "User created successfully", "user_id": user.id}
```

### User Authentication
```python
from werkzeug.security import check_password_hash

def authenticate_user(username, password):
    user = User.find_by_username(username)
    if user and check_password_hash(user.password_hash, password):
        if user.is_active:
            return user
    return None
```

## Testing

### Unit Tests
```python
import unittest
from CancerGenomicsSuite.app import create_app, db
from CancerGenomicsSuite.app.auth.models import User
from werkzeug.security import generate_password_hash

class TestUserModel(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_create_user(self):
        user = User(
            username="testuser",
            password_hash=generate_password_hash("password")
        )
        user.save()
        
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_admin)
    
    def test_find_by_username(self):
        user = User(
            username="testuser",
            password_hash=generate_password_hash("password")
        )
        user.save()
        
        found_user = User.find_by_username("testuser")
        self.assertIsNotNone(found_user)
        self.assertEqual(found_user.username, "testuser")
    
    def test_unique_username(self):
        user1 = User(
            username="testuser",
            password_hash=generate_password_hash("password1")
        )
        user1.save()
        
        user2 = User(
            username="testuser",  # Same username
            password_hash=generate_password_hash("password2")
        )
        
        with self.assertRaises(Exception):
            user2.save()

if __name__ == '__main__':
    unittest.main()
```

### Integration Tests
```python
def test_user_creation_and_authentication():
    # Create user
    user = User(
        username="testuser",
        password_hash=generate_password_hash("SecurePass123!")
    )
    user.save()
    
    # Test authentication
    found_user = User.find_by_username("testuser")
    assert found_user is not None
    assert check_password_hash(found_user.password_hash, "SecurePass123!")
    assert not check_password_hash(found_user.password_hash, "WrongPassword")
```

## Performance Considerations

### Database Indexes
- Username index for fast login lookups
- Email index for email-based authentication
- Active status index for filtering active users
- Admin status index for admin user queries

### Query Optimization
```python
# Efficient user lookup
user = User.query.filter_by(username="testuser").first()

# Batch user operations
active_users = User.query.filter_by(is_active=True).all()

# Pagination for large user lists
users = User.query.paginate(page=1, per_page=20)
```

## Security Considerations

### Password Security
- Always use `generate_password_hash()` for password hashing
- Never store plain text passwords
- Use `check_password_hash()` for password verification

### Input Validation
- Validate username format and length
- Validate email format if provided
- Sanitize all user inputs

### Access Control
- Check `is_active` status before authentication
- Use `is_admin` flag for admin-only operations
- Implement proper session management

## Migration and Deployment

### Database Migration
```python
# Create tables
db.create_all()

# Or use Flask-Migrate for production
flask db init
flask db migrate -m "Create users table"
flask db upgrade
```

### Production Considerations
- Use environment-specific database configurations
- Implement proper backup strategies
- Monitor database performance
- Use connection pooling for high-traffic applications

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure `app` module is properly configured
   - Check database connection settings

2. **Database Errors**
   - Verify database tables exist
   - Check database permissions
   - Ensure proper database URL configuration

3. **Authentication Issues**
   - Verify password hashing is consistent
   - Check user active status
   - Ensure proper session configuration

### Debug Mode
```python
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## Future Enhancements

Planned improvements include:

- **Profile Management**: Extended user profile fields
- **Role-Based Access**: More granular permission system
- **Audit Logging**: User action tracking
- **Password Policies**: Configurable password requirements
- **Account Recovery**: Password reset functionality
- **Two-Factor Authentication**: Additional security layer
- **Social Login**: OAuth integration
- **User Preferences**: Customizable user settings
