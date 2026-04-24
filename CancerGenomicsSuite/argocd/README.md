# ArgoCD Configuration for Cancer Genomics Analysis Suite

This directory contains ArgoCD configurations for deploying and managing the Cancer Genomics Analysis Suite in Kubernetes.

## Overview

ArgoCD is used for GitOps-based continuous deployment of the application and its infrastructure components.

## Files

### Core Configuration
- `argocd-app.yaml` - Main application deployment configuration
- `argocd-project.yaml` - Project definition with permissions and policies
- `argocd-config.yaml` - ArgoCD server configuration

### Component Applications
- `kafka-application.yaml` - Kafka infrastructure and cluster deployment
- `monitoring-application.yaml` - Prometheus, Grafana, and ELK stack deployment

## Prerequisites

1. ArgoCD installed in your Kubernetes cluster
2. Access to the configured Git repositories
3. Proper RBAC permissions for ArgoCD

## Deployment Steps

### 1. Create the Project
```bash
kubectl apply -f argocd-project.yaml
```

### 2. Configure ArgoCD Server
```bash
kubectl apply -f argocd-config.yaml
```

### 3. Deploy Applications
```bash
# Main application
kubectl apply -f argocd-app.yaml

# Kafka infrastructure
kubectl apply -f kafka-application.yaml

# Monitoring stack
kubectl apply -f monitoring-application.yaml
```

## Configuration Details

### Project Configuration
The project includes:
- Source repository access
- Destination cluster and namespace permissions
- Resource whitelist for security
- Role-based access control (RBAC)
- Sync windows for controlled deployments

### Applications
Each application is configured with:
- Automated sync policies
- Self-healing capabilities
- Retry mechanisms
- Resource pruning
- Namespace creation

### Security
- OIDC integration with Keycloak
- RBAC with different user roles
- Resource exclusions for security
- GPG signature verification

## Monitoring

ArgoCD provides built-in monitoring capabilities:
- Application health status
- Sync status and history
- Resource utilization
- Audit logs

## Troubleshooting

### Common Issues
1. **Sync Failures**: Check resource quotas and permissions
2. **Authentication Issues**: Verify OIDC configuration
3. **Repository Access**: Ensure proper Git credentials

### Useful Commands
```bash
# Check application status
kubectl get applications -n argocd

# View application details
kubectl describe application cancer-genomics-analysis-suite -n argocd

# Force sync
kubectl patch application cancer-genomics-analysis-suite -n argocd --type merge -p '{"operation":{"sync":{"syncStrategy":{"force":true}}}}'

# View logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server
```

## Customization

### Environment Variables
Update the following in your deployment:
- Repository URLs
- Domain names
- Resource limits
- Storage classes

### Adding New Applications
1. Create a new YAML file following the existing pattern
2. Update the project configuration if needed
3. Apply the new application manifest

## Best Practices

1. **Use Sync Windows**: Implement sync windows for production deployments
2. **Resource Limits**: Set appropriate resource limits for all components
3. **Monitoring**: Enable monitoring for all applications
4. **Security**: Use RBAC and OIDC for access control
5. **Backup**: Regular backup of ArgoCD configuration

## Support

For issues and questions:
1. Check ArgoCD documentation
2. Review application logs
3. Verify Kubernetes cluster health
4. Contact the development team