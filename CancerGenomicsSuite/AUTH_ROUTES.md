# Authentication Routes Documentation

This document describes the simplified authentication routes for the Cancer Genomics Analysis Suite.

## Overview

The authentication system provides basic user management functionality with the following endpoints:

- **POST /auth/register** - User registration
- **POST /auth/login** - User login
- **POST /auth/logout** - User logout
- **GET /auth/status** - Authentication system status

## API Endpoints

### 1. User Registration

**Endpoint:** `POST /auth/register`

**Description:** Register a new user account.

**Request Body:**
```json
{
    "username": "string (required)",
    "password": "string (required)",
    "email": "string (optional)",
    "first_name": "string (optional)",
    "last_name": "string (optional)"
}
```

**Response Examples:**

Success (201):
```json
{
    "message": "User registered successfully",
    "user_id": 1,
    "username": "testuser"
}
```

Error - User exists (400):
```json
{
    "message": "User already exists"
}
```

Error - Missing data (400):
```json
{
    "message": "Username and password are required"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8050/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "newuser", "password": "SecurePass123!", "email": "newuser@example.com"}'
```

### 2. User Login

**Endpoint:** `POST /auth/login`

**Description:** Authenticate a user and return login information.

**Request Body:**
```json
{
    "username": "string (required)",
    "password": "string (required)"
}
```

**Response Examples:**

Success (200):
```json
{
    "message": "Login successful",
    "user_id": 1,
    "username": "testuser",
    "is_admin": false
}
```

Error - Invalid credentials (401):
```json
{
    "message": "Invalid credentials"
}
```

Error - Account inactive (401):
```json
{
    "message": "Account is inactive"
}
```

Error - Missing data (400):
```json
{
    "message": "Username and password are required"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8050/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "SecurePass123!"}'
```

### 3. User Logout

**Endpoint:** `POST /auth/logout`

**Description:** Log out the current user.

**Request Body:** None

**Response Examples:**

Success (200):
```json
{
    "message": "Logout successful"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8050/auth/logout
```

### 4. Authentication Status

**Endpoint:** `GET /auth/status`

**Description:** Check the status of the authentication system.

**Request Body:** None

**Response Example:**

Success (200):
```json
{
    "message": "Authentication system is operational",
    "endpoints": {
        "login": "/auth/login",
        "register": "/auth/register",
        "logout": "/auth/logout",
        "status": "/auth/status"
    }
}
```

**cURL Example:**
```bash
curl -X GET http://localhost:8050/auth/status
```

## Error Handling

### HTTP Status Codes

- **200 OK** - Request successful
- **201 Created** - Resource created successfully
- **400 Bad Request** - Invalid request data
- **401 Unauthorized** - Authentication failed
- **500 Internal Server Error** - Server error

### Error Response Format

All error responses follow this format:
```json
{
    "message": "Error description"
}
```

## Security Features

### Password Security
- Passwords are hashed using Werkzeug's secure hashing
- Strong password requirements (handled by the auth package)
- Protection against common password patterns

### Input Validation
- All inputs are validated and sanitized
- Required field checking
- Duplicate username prevention

### Audit Logging
- All authentication events are logged
- Failed login attempts are tracked
- User registration events are recorded

## Usage Examples

### Python Requests

```python
import requests

# Register a new user
register_data = {
    "username": "newuser",
    "password": "SecurePass123!",
    "email": "newuser@example.com"
}

response = requests.post(
    "http://localhost:8050/auth/register",
    json=register_data
)

if response.status_code == 201:
    print("User registered successfully")
    print(response.json())
else:
    print("Registration failed")
    print(response.json())

# Login
login_data = {
    "username": "newuser",
    "password": "SecurePass123!"
}

response = requests.post(
    "http://localhost:8050/auth/login",
    json=login_data
)

if response.status_code == 200:
    print("Login successful")
    user_info = response.json()
    print(f"User ID: {user_info['user_id']}")
    print(f"Username: {user_info['username']}")
    print(f"Is Admin: {user_info['is_admin']}")
else:
    print("Login failed")
    print(response.json())
```

### JavaScript Fetch

```javascript
// Register a new user
const registerData = {
    username: "newuser",
    password: "SecurePass123!",
    email: "newuser@example.com"
};

fetch('/auth/register', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(registerData)
})
.then(response => response.json())
.then(data => {
    if (response.ok) {
        console.log('User registered successfully:', data);
    } else {
        console.log('Registration failed:', data);
    }
});

// Login
const loginData = {
    username: "newuser",
    password: "SecurePass123!"
};

fetch('/auth/login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(loginData)
})
.then(response => response.json())
.then(data => {
    if (response.ok) {
        console.log('Login successful:', data);
        // Store user info for future requests
        localStorage.setItem('user', JSON.stringify(data));
    } else {
        console.log('Login failed:', data);
    }
});
```

## Testing

### Manual Testing

Use the provided test script:
```bash
python test_auth_routes.py
```

### cURL Testing

Use the cURL examples provided in each endpoint section, or run:
```bash
python test_auth_routes.py --curl
```

### Automated Testing

```python
import unittest
import requests

class TestAuthRoutes(unittest.TestCase):
    def setUp(self):
        self.base_url = "http://localhost:8050/auth"
    
    def test_register_user(self):
        data = {
            "username": "testuser",
            "password": "TestPass123!"
        }
        response = requests.post(f"{self.base_url}/register", json=data)
        self.assertEqual(response.status_code, 201)
    
    def test_login_user(self):
        data = {
            "username": "testuser",
            "password": "TestPass123!"
        }
        response = requests.post(f"{self.base_url}/login", json=data)
        self.assertEqual(response.status_code, 200)
    
    def test_invalid_login(self):
        data = {
            "username": "testuser",
            "password": "wrongpassword"
        }
        response = requests.post(f"{self.base_url}/login", json=data)
        self.assertEqual(response.status_code, 401)

if __name__ == '__main__':
    unittest.main()
```

## Integration with Flask App

The authentication routes are automatically registered when the Flask app is created:

```python
from CancerGenomicsSuite.app import create_app

app = create_app()
# Authentication routes are now available at /auth/*
```

## Database Requirements

The authentication system requires a `users` table with the following structure:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

## Configuration

The authentication system uses the following configuration from `config/settings.py`:

- Database connection settings
- Security settings (password requirements, session timeout)
- Logging configuration
- Feature flags

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure Flask app is running: `python run_flask_app.py`
   - Check if port 8050 is available

2. **Database Errors**
   - Ensure database is properly configured
   - Check if user table exists
   - Verify database connection

3. **Import Errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python path configuration

4. **Authentication Failures**
   - Verify password requirements are met
   - Check if user account is active
   - Ensure username exists in database

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger('app.auth').setLevel(logging.DEBUG)
```

## Future Enhancements

Planned improvements include:

- Session management with Flask-Login
- JWT token support
- Two-factor authentication
- Password reset functionality
- User profile management endpoints
- Admin user management endpoints
- API key authentication
- OAuth integration
