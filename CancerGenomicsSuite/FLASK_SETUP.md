# Flask Application Setup

This document describes how to set up and run the Flask application for the Cancer Genomics Analysis Suite.

## Overview

The Flask application is built using the application factory pattern and includes:

- **Flask-SQLAlchemy**: Database ORM
- **Flask-CORS**: Cross-origin resource sharing
- **Flask-Login**: User authentication
- **Comprehensive error handling**: Custom error pages and API responses
- **Blueprint architecture**: Modular route organization
- **Configuration management**: Environment-based settings

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment

Copy the environment template and configure your settings:

```bash
cp environment.template .env
```

Edit `.env` with your specific configuration (database URL, API keys, etc.).

### 3. Run the Application

```bash
python run_flask_app.py
```

The application will be available at `http://localhost:8050` (or the port specified in your configuration).

## Application Structure

```
app/
├── __init__.py          # Flask app factory and extension initialization
├── auth/                # Authentication module
│   ├── models.py        # User models
│   └── routes.py        # Auth routes (login, logout, etc.)
├── dashboard/           # Dashboard module
│   ├── layouts.py       # Dashboard layouts
│   └── routes.py        # Dashboard routes
└── db/                  # Database module
    ├── models.py        # Main database models
    └── schema.sql       # Database schema
```

## Key Features

### Application Factory Pattern

The `create_app()` function in `app/__init__.py` creates and configures the Flask application:

```python
from app import create_app

app = create_app()
```

### Extensions

- **SQLAlchemy**: Database operations
- **CORS**: Cross-origin requests
- **Login Manager**: User authentication
- **Error Handlers**: Custom error responses

### Blueprints

- **Auth Blueprint** (`/auth`): User authentication and management
- **Dashboard Blueprint** (`/dashboard`): Main application interface

### API Endpoints

- `GET /`: Main landing page
- `GET /health`: Health check endpoint
- `GET /api/status`: API status with feature flags
- `GET /auth/login`: User login
- `GET /dashboard`: Main dashboard

## Configuration

The application uses the settings from `config/settings.py` which supports:

- Environment-based configuration
- Pydantic validation (if available)
- Fallback simple configuration
- Feature flags for enabling/disabling functionality

## Database

The application automatically:

- Creates database tables on startup
- Runs migrations from `app/db/migrations/`
- Initializes the database connection

## Error Handling

Comprehensive error handling includes:

- HTTP status code handlers (400, 401, 403, 404, 500)
- JSON error responses for API endpoints
- Logging of errors and exceptions
- User-friendly error messages

## Development

### Running in Development Mode

Set `FLASK_ENV=development` in your `.env` file for:

- Debug mode enabled
- Auto-reload on code changes
- Detailed error messages

### Testing

The application includes test configurations and can be run with:

```bash
python -m pytest tests/
```

## Production Deployment

For production deployment:

1. Set `FLASK_ENV=production` in your environment
2. Configure a production database (PostgreSQL recommended)
3. Set up proper logging
4. Use a WSGI server like Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:8050 run_flask_app:app
```

## API Documentation

### Health Check

```bash
curl http://localhost:8050/health
```

Response:
```json
{
  "status": "healthy",
  "app_name": "Cancer Genomics Analysis Suite",
  "version": "1.0.0",
  "environment": "development"
}
```

### API Status

```bash
curl http://localhost:8050/api/status
```

Response:
```json
{
  "status": "operational",
  "features": {
    "gene_expression_analysis": true,
    "mutation_analysis": true,
    "machine_learning": true,
    "pathway_analysis": true,
    "multi_omics_integration": true
  },
  "external_services": {
    "redis_enabled": false,
    "email_enabled": true,
    "cloud_storage_enabled": false
  }
}
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**: Check your `DATABASE_URL` in `.env`
2. **Import Errors**: Ensure all dependencies are installed
3. **Port Already in Use**: Change the `PORT` in your configuration

### Logs

Check the application logs for detailed error information. Logs are configured in `config/settings.py` and can be written to files or console.

## Next Steps

1. Implement user authentication logic in `app/auth/routes.py`
2. Add more dashboard functionality in `app/dashboard/routes.py`
3. Create additional database models as needed
4. Add API endpoints for specific analysis modules
5. Implement file upload and processing capabilities
