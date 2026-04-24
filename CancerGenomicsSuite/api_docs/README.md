# API Documentation

This directory contains the API documentation for the Cancer Genomics Analysis Suite.

## Files

- `openapi.yaml` - OpenAPI 3.0 specification file
- `swagger_ui.py` - Flask integration for Swagger UI
- `README.md` - This documentation file

## API Documentation Features

### Interactive Documentation
- **Swagger UI**: Interactive API documentation with try-it-out functionality
- **OpenAPI 3.0**: Standard specification format
- **Authentication**: JWT token integration
- **Examples**: Comprehensive request/response examples

### Available Endpoints

#### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /auth/profile` - Get user profile

#### Health & Status
- `GET /health` - Health check
- `GET /api/status` - API status with feature flags

#### BLAST Analysis
- `POST /blast/analyze` - Run BLAST sequence analysis
- `GET /blast/jobs/{job_id}` - Get BLAST job status

#### Variant Annotation
- `POST /annotation/annotate` - Annotate genomic variants

#### Machine Learning
- `POST /ml/predict` - Run ML predictions

#### Reports
- `POST /reports/generate` - Generate analysis reports

#### Data Management
- `POST /data/upload` - Upload data files

## Accessing the Documentation

### Development
```bash
# Start the Flask application
python run_flask_app.py

# Access Swagger UI
http://localhost:8050/api/docs/
```

### Production
```bash
# Access via your domain
https://api.cancer-genomics.com/api/docs/
```

## Integration with Flask App

To integrate the API documentation with your Flask application:

```python
from api_docs.swagger_ui import register_api_docs

# In your Flask app initialization
app = create_app()
register_api_docs(app)
```

## Customization

### Updating the OpenAPI Specification

1. Edit `openapi.yaml` to add new endpoints or modify existing ones
2. The changes will be automatically reflected in Swagger UI
3. Restart the Flask application to see changes

### Adding Authentication

The Swagger UI automatically handles JWT authentication:
1. Use the "Authorize" button in Swagger UI
2. Enter your JWT token
3. All subsequent requests will include the token

### Custom Styling

Modify the CSS in `swagger_ui.py` to customize the appearance:
- Change color scheme
- Add custom branding
- Modify layout

## API Examples

### Authentication
```bash
# Login
curl -X POST "http://localhost:8050/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "secure_password"
  }'
```

### BLAST Analysis
```bash
# Run BLAST analysis
curl -X POST "http://localhost:8050/blast/analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{
    "sequences": [
      {
        "id": "seq_001",
        "sequence": "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "description": "Sample sequence 1"
      }
    ],
    "database": "cancer_genes",
    "parameters": {
      "evalue": 1e-5,
      "max_target_seqs": 100
    }
  }'
```

### Variant Annotation
```bash
# Annotate variants
curl -X POST "http://localhost:8050/annotation/annotate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{
    "variants": [
      {
        "chromosome": "17",
        "position": 7574003,
        "reference": "G",
        "alternate": "A",
        "gene_symbol": "TP53"
      }
    ],
    "annotation_sources": ["ensembl", "clinvar", "cosmic"]
  }'
```

## Rate Limiting

The API implements rate limiting:
- General endpoints: 100 requests per minute
- Authentication endpoints: 5 requests per minute
- File upload endpoints: 10 requests per minute

## Error Handling

All API endpoints return consistent error responses:

```json
{
  "error": "Validation error",
  "message": "Invalid input parameters",
  "details": {
    "field": "specific error message"
  },
  "timestamp": "2025-01-01T12:00:00Z",
  "request_id": "req_12345"
}
```

## Security

- **JWT Authentication**: All protected endpoints require valid JWT tokens
- **HTTPS**: Production endpoints use HTTPS
- **Rate Limiting**: Prevents abuse and ensures fair usage
- **Input Validation**: All inputs are validated and sanitized
- **CORS**: Proper CORS headers for cross-origin requests

## Monitoring

The API includes comprehensive monitoring:
- Health check endpoints
- Metrics collection
- Request/response logging
- Performance monitoring

## Support

For API support:
- Check the interactive documentation at `/api/docs/`
- Review the OpenAPI specification in `openapi.yaml`
- Contact the development team for assistance
