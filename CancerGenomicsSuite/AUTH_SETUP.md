# Authentication System Setup

This document describes the authentication system for the Cancer Genomics Analysis Suite.

## Overview

The authentication system provides:

- **User Management**: Registration, login, logout, profile management
- **Security**: Password hashing, input validation, session management
- **Authorization**: Role-based access control and permission system
- **Audit Logging**: Security event logging for compliance
- **API Integration**: RESTful authentication endpoints
- **Session Management**: Secure session handling with timeout

## Architecture

### Core Components

1. **`app/auth/__init__.py`**: Main authentication package with utilities and functions
2. **`app/auth/models.py`**: User model and database operations
3. **`app/auth/routes.py`**: Authentication routes and API endpoints

### Security Features

- **Password Security**: Strong password requirements and secure hashing
- **Input Validation**: Sanitization and validation of all user inputs
- **Session Security**: Secure session tokens and timeout management
- **Audit Logging**: Comprehensive logging of authentication events
- **Role-Based Access**: Hierarchical permission system

## User Roles and Permissions

### Role Hierarchy

1. **Admin** (Level 100)
   - Full system access
   - User management
   - System administration

2. **Researcher** (Level 80)
   - Full analysis capabilities
   - Data management
   - Report generation

3. **Analyst** (Level 60)
   - Analysis and reporting
   - Data export
   - Limited data modification

4. **Viewer** (Level 40)
   - Read-only access
   - Report viewing
   - Limited data access

5. **Guest** (Level 20)
   - Public data only
   - Minimal access

### Permissions

- `read_data`: Read genomic and clinical data
- `write_data`: Upload and modify data
- `run_analysis`: Execute analysis workflows
- `export_results`: Export analysis results
- `manage_own_data`: Manage personal data and projects
- `view_reports`: View generated reports
- `manage_users`: Manage user accounts and permissions
- `system_admin`: System administration tasks
- `view_public_data`: View publicly available data
- `api_access`: Access to API endpoints

## API Endpoints

### Authentication

#### Login
```http
POST /auth/login
Content-Type: application/json

{
    "username": "user@example.com",
    "password": "secure_password",
    "remember": false
}
```

#### Logout
```http
GET /auth/logout
```

#### Registration
```http
POST /auth/register
Content-Type: application/json

{
    "username": "newuser",
    "email": "user@example.com",
    "password": "secure_password",
    "confirm_password": "secure_password",
    "first_name": "John",
    "last_name": "Doe"
}
```

### User Management

#### Get Profile
```http
GET /auth/profile
```

#### Update Profile
```http
PUT /auth/profile/update
Content-Type: application/json

{
    "first_name": "John",
    "last_name": "Smith",
    "email": "newemail@example.com"
}
```

#### Change Password
```http
POST /auth/change-password
Content-Type: application/json

{
    "old_password": "old_password",
    "new_password": "new_secure_password",
    "confirm_password": "new_secure_password"
}
```

### Admin Endpoints

#### List Users (Admin Only)
```http
GET /auth/api/auth/users
```

#### Manage User (Admin Only)
```http
GET /auth/api/auth/users/{user_id}
PUT /auth/api/auth/users/{user_id}
DELETE /auth/api/auth/users/{user_id}
```

#### Authentication Status
```http
GET /auth/api/auth/status
```

## Usage Examples

### Python Integration

```python
from CancerGenomicsSuite.app.auth import (
    authenticate_user, create_user, require_permission, 
    require_admin, has_permission
)

# Authenticate user
user = authenticate_user('username', 'password')

# Create new user
user = create_user(
    username='newuser',
    email='user@example.com',
    password='secure_password',
    role='researcher'
)

# Check permissions
if has_permission(user, 'run_analysis'):
    # User can run analysis
    pass

# Use decorators
@require_permission('manage_users')
def admin_function():
    pass

@require_admin
def admin_only_function():
    pass
```

### Flask Route Protection

```python
from flask import Blueprint
from CancerGenomicsSuite.app.auth import require_permission, require_admin

bp = Blueprint('protected', __name__)

@bp.route('/admin-only')
@require_admin
def admin_only():
    return "Admin only content"

@bp.route('/analysis')
@require_permission('run_analysis')
def run_analysis():
    return "Analysis endpoint"
```

## Password Requirements

### Security Standards

- **Minimum Length**: 8 characters
- **Character Requirements**:
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one number
  - At least one special character
- **Forbidden Patterns**: Common passwords like "password", "123456"
- **Strength Levels**: Weak, Medium, Strong, Very Strong

### Password Validation

```python
from CancerGenomicsSuite.app.auth import validate_password

result = validate_password('MySecure123!')
if result['valid']:
    print("Password is valid")
else:
    print("Errors:", result['errors'])
```

## Session Management

### Session Features

- **Secure Tokens**: Cryptographically secure session tokens
- **Timeout**: Configurable session timeout (default: 1 hour)
- **Remember Me**: Extended sessions for trusted devices
- **Validation**: Session integrity checking
- **Cleanup**: Automatic session cleanup

### Session Configuration

```python
# Session settings in config
SESSION_TIMEOUT = 3600  # 1 hour
REMEMBER_ME_DURATION = 86400 * 30  # 30 days
SECURE_SESSION_COOKIES = True
```

## Security Best Practices

### Input Validation

- **Sanitization**: All user inputs are sanitized
- **Length Limits**: Input length restrictions
- **Type Validation**: Proper data type validation
- **SQL Injection Prevention**: Parameterized queries

### Audit Logging

All authentication events are logged:

- Login attempts (successful and failed)
- Logout events
- Password changes
- Profile updates
- User management actions
- Permission changes

### Error Handling

- **No Information Leakage**: Generic error messages
- **Rate Limiting**: Protection against brute force attacks
- **Account Lockout**: Temporary lockout after failed attempts
- **Secure Headers**: Security headers for all responses

## Configuration

### Environment Variables

```bash
# Authentication settings
ENABLE_AUTHENTICATION=True
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
PERMANENT_SESSION_LIFETIME=86400

# Password requirements
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_SPECIAL_CHARS=True

# Security settings
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=900
```

### Database Setup

The authentication system requires the following database tables:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

## Testing

### Unit Tests

```python
import pytest
from CancerGenomicsSuite.app.auth import authenticate_user, create_user, validate_password

def test_password_validation():
    result = validate_password('Weak123')
    assert not result['valid']
    assert 'uppercase' in str(result['errors'])

def test_user_creation():
    user = create_user('testuser', 'test@example.com', 'SecurePass123!')
    assert user.username == 'testuser'
    assert user.email == 'test@example.com'

def test_authentication():
    user = authenticate_user('testuser', 'SecurePass123!')
    assert user is not None
    assert user.username == 'testuser'
```

### Integration Tests

```python
def test_login_endpoint(client):
    response = client.post('/auth/login', json={
        'username': 'testuser',
        'password': 'SecurePass123!'
    })
    assert response.status_code == 200
    assert 'session' in response.json
```

## Deployment Considerations

### Production Security

1. **HTTPS Only**: All authentication must use HTTPS
2. **Secure Cookies**: Set secure cookie flags
3. **Database Security**: Encrypt sensitive data
4. **Log Monitoring**: Monitor authentication logs
5. **Regular Updates**: Keep dependencies updated

### Performance

- **Session Storage**: Use Redis for session storage in production
- **Database Indexing**: Index username and email fields
- **Caching**: Cache user permissions and roles
- **Connection Pooling**: Use database connection pooling

### Monitoring

- **Failed Login Attempts**: Monitor for brute force attacks
- **Unusual Activity**: Track unusual login patterns
- **Session Anomalies**: Monitor for session hijacking
- **Permission Changes**: Audit permission modifications

## Troubleshooting

### Common Issues

1. **Login Failures**
   - Check password requirements
   - Verify user account is active
   - Check database connection

2. **Session Issues**
   - Verify session timeout settings
   - Check cookie configuration
   - Validate session storage

3. **Permission Errors**
   - Verify user roles and permissions
   - Check decorator usage
   - Validate permission strings

### Debug Mode

Enable debug logging for authentication:

```python
import logging
logging.getLogger('app.auth').setLevel(logging.DEBUG)
```

## Future Enhancements

### Planned Features

- **Two-Factor Authentication**: SMS/Email/TOTP support
- **OAuth Integration**: Google, GitHub, etc.
- **JWT Tokens**: Stateless authentication option
- **API Key Management**: Programmatic access
- **Advanced Roles**: Custom role creation
- **Password Policies**: Configurable password requirements
- **Account Recovery**: Secure password reset
- **Multi-Factor Authentication**: Hardware token support
