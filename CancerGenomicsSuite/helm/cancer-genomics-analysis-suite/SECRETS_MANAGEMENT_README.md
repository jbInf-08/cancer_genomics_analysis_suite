# Cancer Genomics Analysis Suite - Secrets Management

This document provides comprehensive documentation for the secrets management solution integrated with the Cancer Genomics Analysis Suite Helm chart.

## Overview

The secrets management solution provides a robust, scalable, and secure approach to managing secrets across multiple environments using:

- **HashiCorp Vault** - Primary secrets management
- **SealedSecrets** - Kubernetes-native secrets encryption
- **Cloud Secret Managers** - AWS Secrets Manager, GCP Secret Manager, Azure Key Vault
- **Automatic Secret Rotation** - Scheduled rotation with validation
- **Comprehensive Monitoring** - Grafana dashboards and Prometheus alerts
- **CI/CD Integration** - GitHub Actions workflows

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vault         │    │  SealedSecrets  │    │ Cloud Secrets   │
│   (Primary)     │    │  (Backup)       │    │ (External)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Kubernetes    │
                    │   Secrets       │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Applications  │
                    │   (Pods)        │
                    └─────────────────┘
```

## Features

### 🔐 Multi-Strategy Secrets Management
- **Vault**: Primary secrets storage with encryption, access control, and audit logging
- **SealedSecrets**: Kubernetes-native encryption for GitOps workflows
- **Cloud Secret Managers**: Integration with AWS, GCP, and Azure secret services
- **Hybrid Mode**: Combine multiple strategies for maximum security

### 🔄 Automatic Secret Rotation
- Scheduled rotation of database passwords, API keys, and certificates
- Configurable rotation intervals (30-365 days)
- Automatic validation after rotation
- Rollback capability on rotation failure

### 📊 Comprehensive Monitoring
- Grafana dashboards for secrets management
- Prometheus metrics and alerting
- Real-time monitoring of secret health
- Audit logging and compliance reporting

### 🚀 CI/CD Integration
- GitHub Actions workflows for automated deployment
- Dynamic secrets strategy selection
- Environment-specific configurations
- Automated testing and validation

## Quick Start

### 1. Prerequisites

```bash
# Install required tools
kubectl version --client
helm version
vault version
kubeseal --version
```

### 2. Configure Environment

```bash
# Set environment variables
export VAULT_ADDR="https://vault.cancer-genomics.local:8200"
export VAULT_NAMESPACE="cancer-genomics"
export KUBERNETES_NAMESPACE="cancer-genomics"
export SECRETS_STRATEGY="vault"  # vault, sealed-secrets, cloud-manager, hybrid
```

### 3. Deploy with Vault

```bash
# Run the deployment orchestration script
chmod +x scripts/deploy-orchestration.sh
./scripts/deploy-orchestration.sh deploy
```

### 4. Verify Deployment

```bash
# Check pod status
kubectl get pods -n cancer-genomics

# Check secrets
kubectl get secrets -n cancer-genomics

# Check Vault status
vault status
```

## Configuration

### Values.yaml Configuration

The `values.yaml` file contains comprehensive configuration for all secrets management strategies:

```yaml
# Global secrets management configuration
global:
  secretsStrategy: "vault"  # vault, sealed-secrets, cloud-manager, hybrid
  
  vault:
    enabled: true
    address: "https://vault.cancer-genomics.local:8200"
    namespace: "cancer-genomics"
    authMethod: "kubernetes"
    role: "cancer-genomics-role"
    path: "secret/cancer-genomics"

# Enhanced secrets management
secretsManagement:
  strategy: "vault"
  
  vault:
    enabled: true
    rotation:
      enabled: true
      schedule: "0 2 * * *"  # Daily at 2 AM
      policies:
        database:
          enabled: true
          interval: "30d"
          autoRestart: true
        app:
          enabled: true
          interval: "90d"
          autoRestart: true
  
  sealedSecrets:
    enabled: true
    controller:
      namespace: "kube-system"
      name: "sealed-secrets-controller"
  
  cloudSecretManager:
    enabled: false
    provider: "aws"  # aws, gcp, azure
```

### Environment-Specific Values

#### Staging Environment
```yaml
# values-staging.yaml
global:
  environment: "staging"
  domain: "staging.cancer-genomics.local"
  
secretsManagement:
  vault:
    address: "https://vault-staging.cancer-genomics.local:8200"
    namespace: "cancer-genomics-staging"
  
web:
  replicaCount: 2
  resources:
    limits:
      cpu: 1000m
      memory: 2Gi
    requests:
      cpu: 250m
      memory: 512Mi
```

#### Production Environment
```yaml
# values-production.yaml
global:
  environment: "production"
  domain: "cancer-genomics.yourdomain.com"
  
secretsManagement:
  vault:
    address: "https://vault.cancer-genomics.local:8200"
    namespace: "cancer-genomics"
  
security:
  mtls:
    enabled: true
  waf:
    enabled: true
  podSecurityPolicy:
    enabled: true
  
web:
  replicaCount: 3
  resources:
    limits:
      cpu: 2000m
      memory: 4Gi
    requests:
      cpu: 500m
      memory: 1Gi
```

## Scripts

### 1. Vault Provisioning (`scripts/vault-provisioning.sh`)

Automates Vault setup, configuration, and secret management:

```bash
# Basic usage
./scripts/vault-provisioning.sh

# With custom configuration
export VAULT_ADDR="https://vault.example.com:8200"
export VAULT_NAMESPACE="cancer-genomics"
./scripts/vault-provisioning.sh
```

**Features:**
- Vault server configuration
- Secret engines setup (KV v2, Database, PKI, Transit)
- Authentication methods (Kubernetes, AWS, GCP, Azure)
- Policy creation and management
- Initial secrets creation
- Backup and restore functionality

### 2. Secret Rotation (`scripts/secret-rotation.sh`)

Handles automatic rotation of secrets:

```bash
# Rotate all secrets
./scripts/secret-rotation.sh rotate

# Rotate specific secrets
./scripts/secret-rotation.sh rotate database app redis

# Check if rotation is needed
./scripts/secret-rotation.sh check database 30d

# Validate rotation
./scripts/secret-rotation.sh validate database
```

**Features:**
- Configurable rotation intervals
- Automatic validation after rotation
- Rollback capability
- Backup before rotation
- Alert notifications

### 3. Cloud Secrets Integration (`scripts/cloud-secrets-integration.sh`)

Integrates with cloud secret managers:

```bash
# Create initial secrets
./scripts/cloud-secrets-integration.sh create

# Sync secrets to Kubernetes
./scripts/cloud-secrets-integration.sh sync

# List all secrets
./scripts/cloud-secrets-integration.sh list

# Backup secrets
./scripts/cloud-secrets-integration.sh backup
```

**Supported Providers:**
- AWS Secrets Manager
- GCP Secret Manager
- Azure Key Vault

### 4. Deployment Orchestration (`scripts/deploy-orchestration.sh`)

Comprehensive deployment orchestration:

```bash
# Deploy with default settings
./scripts/deploy-orchestration.sh deploy

# Deploy with custom configuration
export SECRETS_STRATEGY="hybrid"
export ENVIRONMENT="production"
./scripts/deploy-orchestration.sh deploy

# Validate deployment
./scripts/deploy-orchestration.sh validate

# Rollback deployment
./scripts/deploy-orchestration.sh rollback
```

## Monitoring and Alerting

### Grafana Dashboards

The solution includes comprehensive Grafana dashboards for:

- Vault health and performance
- Secret rotation status
- Secret injection monitoring
- Cloud secret manager status
- Security compliance metrics

### Prometheus Alerts

Key alerting rules include:

- **VaultUnavailable**: Vault is down or unhealthy
- **VaultSealed**: Vault is sealed
- **SecretRotationFailed**: Secret rotation failed
- **SecretInjectionFailed**: Secret injection failed
- **SecretExpiringSoon**: Secret expires within 24 hours
- **UnauthorizedSecretAccess**: Unauthorized access detected

### Alert Configuration

```yaml
# grafana-alerting-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cancer-genomics-secrets-alerts
spec:
  groups:
  - name: vault-health
    rules:
    - alert: VaultUnavailable
      expr: vault_health_status != 1
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Vault is unavailable or unhealthy"
        description: "Vault health check failed for {{ $labels.instance }}"
```

## CI/CD Integration

### GitHub Actions Workflow

The solution includes a comprehensive GitHub Actions workflow (`deploy-with-secrets-management.yml`) that:

1. **Security Scanning**: Trivy vulnerability scanning, Snyk security checks
2. **Build and Test**: Docker image building, unit tests, coverage reporting
3. **Secrets Setup**: Dynamic secrets management strategy selection
4. **Deployment**: Environment-specific deployments (staging/production)
5. **Validation**: Comprehensive health checks and integration tests
6. **Monitoring**: Post-deployment validation and reporting

### Workflow Triggers

- **Push to main**: Deploy to production
- **Push to develop**: Deploy to staging
- **Pull Request**: Run tests and security scans
- **Manual**: Workflow dispatch with custom parameters

### Environment Variables

Required GitHub Secrets:

```bash
# Vault Configuration
VAULT_ADDR_STAGING
VAULT_ADDR_PRODUCTION
VAULT_NAMESPACE_STAGING
VAULT_NAMESPACE_PRODUCTION
VAULT_ROLE_STAGING
VAULT_ROLE_PRODUCTION

# Kubernetes Configuration
KUBECONFIG_STAGING
KUBECONFIG_PRODUCTION

# Cloud Provider Configuration
CLOUD_PROVIDER
AWS_REGION
GCP_PROJECT_ID
AZURE_KEY_VAULT_NAME

# Domain Configuration
DOMAIN_STAGING
DOMAIN_PRODUCTION
API_DOMAIN_STAGING
API_DOMAIN_PRODUCTION
```

## Security Best Practices

### 1. Secret Rotation

- Rotate database passwords every 30 days
- Rotate application secrets every 90 days
- Rotate API keys manually or annually
- Use strong, randomly generated passwords

### 2. Access Control

- Implement least privilege access
- Use Kubernetes RBAC for pod access
- Enable Vault audit logging
- Monitor secret access patterns

### 3. Encryption

- Use TLS for all communications
- Encrypt secrets at rest and in transit
- Use strong encryption algorithms
- Regularly rotate encryption keys

### 4. Monitoring

- Monitor secret access patterns
- Alert on unauthorized access attempts
- Track secret rotation status
- Audit secret modifications

## Troubleshooting

### Common Issues

#### 1. Vault Connection Issues

```bash
# Check Vault status
vault status

# Check network connectivity
curl -k https://vault.cancer-genomics.local:8200/v1/sys/health

# Check authentication
vault auth -method=kubernetes role=cancer-genomics-role
```

#### 2. Secret Injection Failures

```bash
# Check pod logs
kubectl logs -n cancer-genomics deployment/cancer-genomics-web

# Check secret status
kubectl get secrets -n cancer-genomics

# Check Vault policies
vault policy read cancer-genomics-policy
```

#### 3. Rotation Failures

```bash
# Check rotation logs
kubectl logs -n cancer-genomics job/secret-rotation

# Validate secret access
./scripts/secret-rotation.sh validate database

# Check backup status
ls -la /tmp/secret-backup-*
```

### Debug Commands

```bash
# Check all components
kubectl get all -n cancer-genomics
kubectl get secrets -n cancer-genomics
kubectl get configmaps -n cancer-genomics

# Check Vault status
vault status
vault auth -method=kubernetes role=cancer-genomics-role

# Check SealedSecrets
kubectl get sealedsecrets -n cancer-genomics
kubeseal --fetch-cert

# Check monitoring
kubectl get servicemonitors -n cancer-genomics
kubectl get prometheusrules -n cancer-genomics
```

## Performance Optimization

### 1. Vault Performance

- Use Vault clustering for high availability
- Enable Vault caching for frequently accessed secrets
- Use appropriate storage backend (Consul, etcd, Raft)
- Monitor Vault metrics and performance

### 2. Secret Injection

- Use init containers for secret injection
- Implement secret caching in applications
- Use sidecar containers for dynamic secret updates
- Monitor secret injection latency

### 3. Rotation Performance

- Schedule rotations during low-traffic periods
- Use batch rotation for multiple secrets
- Implement gradual rotation for critical secrets
- Monitor rotation performance metrics

## Compliance and Auditing

### 1. Audit Logging

- Enable Vault audit logging
- Log all secret access and modifications
- Store audit logs securely
- Implement log retention policies

### 2. Compliance Reporting

- Generate compliance reports
- Track secret rotation compliance
- Monitor access patterns
- Document security controls

### 3. Regulatory Requirements

- HIPAA compliance for healthcare data
- SOC 2 compliance for security controls
- GDPR compliance for data protection
- PCI DSS compliance for payment data

## Backup and Disaster Recovery

### 1. Backup Strategy

- Regular Vault backups
- SealedSecrets public key backup
- Cloud secret manager backups
- Kubernetes secret backups

### 2. Recovery Procedures

- Vault disaster recovery
- Secret restoration procedures
- Application recovery testing
- Documentation and runbooks

### 3. Testing

- Regular backup testing
- Disaster recovery drills
- Secret rotation testing
- Monitoring system testing

## Support and Maintenance

### 1. Regular Maintenance

- Update Vault and SealedSecrets versions
- Rotate certificates and keys
- Update security policies
- Review and update documentation

### 2. Monitoring

- Monitor system health
- Track performance metrics
- Review security alerts
- Analyze audit logs

### 3. Support

- Document troubleshooting procedures
- Maintain runbooks
- Provide training for operations team
- Establish escalation procedures

## Conclusion

This comprehensive secrets management solution provides a robust, scalable, and secure approach to managing secrets in the Cancer Genomics Analysis Suite. The multi-strategy approach ensures high availability and security, while the automated rotation and monitoring capabilities provide operational excellence.

For additional support or questions, please refer to the troubleshooting section or contact the operations team.
