# Docker Deployment Scripts

This directory contains comprehensive Docker deployment scripts for the Cancer Genomics Analysis Suite.

## Scripts Overview

### 1. `build.sh` - Docker Image Builder
Builds Docker images with various options and configurations.

**Features:**
- Multi-architecture builds (amd64, arm64)
- Build cache optimization
- Custom tags and registries
- Build argument injection
- Verbose output options

**Usage:**
```bash
# Basic build
./build.sh

# Build and push with custom tag
./build.sh -t v1.0.0 -p

# Multi-architecture build
./build.sh -m -p

# Build with custom registry
./build.sh -r ghcr.io -u myusername -t dev
```

### 2. `push.sh` - Docker Image Pusher
Pushes Docker images to various registries.

**Features:**
- Multiple registry support (Docker Hub, GHCR, Quay.io)
- Batch tag pushing
- Authentication handling
- Dry-run mode

**Usage:**
```bash
# Push latest tag
./push.sh

# Push specific tag
./push.sh -t v1.0.0

# Push to GitHub Container Registry
./push.sh -r ghcr.io -u myusername

# Push all local tags
./push.sh -a
```

### 3. `deploy.sh` - Complete Deployment
Handles the complete deployment workflow: build, push, and deploy.

**Features:**
- Multi-stage deployment
- Environment-specific configurations
- Kubernetes deployment
- Health checks
- Rollback capabilities

**Usage:**
```bash
# Full deployment to production
./deploy.sh -b -p -d -e prod -t v1.0.0

# Deploy to development
./deploy.sh -b -e dev -t dev

# Deploy existing image
./deploy.sh -d -e staging -t latest
```

### 4. `cleanup.sh` - Docker Cleanup
Cleans up Docker images, containers, volumes, and networks.

**Features:**
- Selective cleanup options
- Tag preservation
- Dry-run mode
- System information display

**Usage:**
```bash
# Clean up images only
./cleanup.sh -i

# Clean up everything
./cleanup.sh -a

# Keep specific tags
./cleanup.sh -i -k "latest,dev"

# Dry run
./cleanup.sh -d
```

## Quick Start

### 1. Make Scripts Executable
```bash
chmod +x scripts/docker/*.sh
```

### 2. Set Environment Variables
```bash
export DOCKER_HUB_USERNAME="your-username"
export DOCKER_HUB_TOKEN="your-token"
export GITHUB_TOKEN="your-github-token"
```

### 3. Build and Deploy
```bash
# Build image
./scripts/docker/build.sh -t v1.0.0

# Push to registry
./scripts/docker/push.sh -t v1.0.0

# Deploy to Kubernetes
./scripts/docker/deploy.sh -d -e prod -t v1.0.0
```

## Environment Configuration

### Development
```bash
# Build and deploy to development
./scripts/docker/deploy.sh -b -e dev -t dev
```

### Staging
```bash
# Build, push, and deploy to staging
./scripts/docker/deploy.sh -b -p -d -e staging -t staging
```

### Production
```bash
# Full production deployment
./scripts/docker/deploy.sh -b -p -d -e prod -t v1.0.0
```

## Registry Support

### Docker Hub
```bash
# Default registry
./scripts/docker/push.sh -r docker.io -u your-username
```

### GitHub Container Registry
```bash
# Push to GHCR
./scripts/docker/push.sh -r ghcr.io -u your-username
```

### Quay.io
```bash
# Push to Quay.io
./scripts/docker/push.sh -r quay.io -u your-username
```

## Multi-Architecture Builds

Build for multiple architectures (amd64, arm64):

```bash
# Build multi-arch image
./scripts/docker/build.sh -m -p

# Deploy multi-arch image
./scripts/docker/deploy.sh -b -m -p -d -e prod -t v1.0.0
```

## Kubernetes Deployment

### Prerequisites
- kubectl installed and configured
- Kubernetes cluster access
- k8s/ directory with manifests

### Deploy to Kubernetes
```bash
# Deploy to specific environment
./scripts/docker/deploy.sh -d -e prod -t v1.0.0

# Deploy with custom namespace
NAMESPACE="my-namespace" ./scripts/docker/deploy.sh -d -e prod -t v1.0.0
```

### Health Checks
The deployment script automatically performs health checks:
- Waits for pod readiness
- Checks service endpoints
- Validates application health

## Cleanup Operations

### Clean Up Images
```bash
# Remove old images (keep latest 3)
./scripts/docker/cleanup.sh -i

# Keep specific tags
./scripts/docker/cleanup.sh -i -k "latest,dev,staging"
```

### Clean Up Everything
```bash
# Clean up all Docker resources
./scripts/docker/cleanup.sh -a -f
```

### Dry Run
```bash
# See what would be cleaned up
./scripts/docker/cleanup.sh -d
```

## Troubleshooting

### Common Issues

1. **Docker not running**
   ```bash
   # Start Docker
   sudo systemctl start docker
   ```

2. **Authentication failed**
   ```bash
   # Login to registry
   docker login
   ```

3. **Kubernetes connection failed**
   ```bash
   # Check kubectl configuration
   kubectl cluster-info
   ```

4. **Build failed**
   ```bash
   # Check Dockerfile
   docker build -t test .
   ```

### Debug Mode
```bash
# Verbose output
./scripts/docker/build.sh -v
./scripts/docker/deploy.sh -v
```

### Logs
Check Docker and Kubernetes logs:
```bash
# Docker logs
docker logs <container-id>

# Kubernetes logs
kubectl logs -f deployment/cancer-genomics-web -n cancer-genomics
```

## Security Considerations

### Secrets Management
- Use environment variables for sensitive data
- Never commit tokens or passwords
- Use Kubernetes secrets for production

### Image Security
- Scan images for vulnerabilities
- Use minimal base images
- Keep images updated

### Registry Security
- Use private registries for production
- Implement access controls
- Monitor registry usage

## Best Practices

### Build Optimization
- Use multi-stage builds
- Leverage build cache
- Minimize image layers
- Use .dockerignore

### Deployment Strategy
- Use rolling updates
- Implement health checks
- Monitor deployments
- Have rollback plans

### Resource Management
- Set resource limits
- Monitor resource usage
- Clean up regularly
- Use resource quotas

## Integration with CI/CD

### GitHub Actions
The scripts integrate with GitHub Actions workflows:
- Automatic builds on push
- Multi-architecture support
- Registry pushing
- Kubernetes deployment

### Jenkins
For Jenkins integration:
```groovy
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh './scripts/docker/build.sh -t ${BUILD_NUMBER}'
            }
        }
        stage('Push') {
            steps {
                sh './scripts/docker/push.sh -t ${BUILD_NUMBER}'
            }
        }
        stage('Deploy') {
            steps {
                sh './scripts/docker/deploy.sh -d -e prod -t ${BUILD_NUMBER}'
            }
        }
    }
}
```

## Support

For issues or questions:
1. Check the script help: `./script.sh -h`
2. Review the logs and error messages
3. Verify environment configuration
4. Check Docker and Kubernetes status
5. Contact the development team
