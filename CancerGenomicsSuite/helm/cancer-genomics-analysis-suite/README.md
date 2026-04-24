# Cancer Genomics Analysis Suite Helm Chart

This Helm chart deploys the Cancer Genomics Analysis Suite on a Kubernetes cluster.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- PostgreSQL 12+ (or use the included PostgreSQL chart)
- Redis 6+ (or use the included Redis chart)

## Installing the Chart

To install the chart with the release name `cancer-genomics`:

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm install cancer-genomics ./helm/cancer-genomics-analysis-suite
```

## Uninstalling the Chart

To uninstall/delete the `cancer-genomics` deployment:

```bash
helm uninstall cancer-genomics
```

## Configuration

The following table lists the configurable parameters and their default values.

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imageRegistry` | Global Docker image registry | `""` |
| `global.imagePullSecrets` | Global Docker registry secret names | `[]` |
| `global.storageClass` | Global storage class for dynamic provisioning | `""` |

### Image Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.registry` | Image registry | `docker.io` |
| `image.repository` | Image repository | `your-username/cancer-genomics-analysis-suite` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `image.pullSecrets` | Image pull secrets | `[]` |

### Web Application Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `web.replicaCount` | Number of web application replicas | `3` |
| `web.service.type` | Web service type | `ClusterIP` |
| `web.service.port` | Web service port | `8050` |
| `web.resources.limits.cpu` | CPU limit | `1000m` |
| `web.resources.limits.memory` | Memory limit | `2Gi` |
| `web.resources.requests.cpu` | CPU request | `250m` |
| `web.resources.requests.memory` | Memory request | `512Mi` |

### Celery Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `celery.worker.replicaCount` | Number of Celery worker replicas | `2` |
| `celery.beat.replicaCount` | Number of Celery beat replicas | `1` |
| `celery.worker.resources.limits.cpu` | Worker CPU limit | `500m` |
| `celery.worker.resources.limits.memory` | Worker memory limit | `1Gi` |
| `celery.beat.resources.limits.cpu` | Beat CPU limit | `200m` |
| `celery.beat.resources.limits.memory` | Beat memory limit | `512Mi` |

### PostgreSQL Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable PostgreSQL | `true` |
| `postgresql.auth.postgresPassword` | PostgreSQL password | `postgres-password` |
| `postgresql.auth.username` | PostgreSQL username | `postgres` |
| `postgresql.auth.password` | PostgreSQL password | `postgres-password` |
| `postgresql.auth.database` | PostgreSQL database | `genomics_db` |
| `postgresql.primary.persistence.size` | PostgreSQL storage size | `20Gi` |

### Redis Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Enable Redis | `true` |
| `redis.auth.enabled` | Enable Redis authentication | `false` |
| `redis.master.persistence.size` | Redis storage size | `8Gi` |

### Ingress Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.hosts[0].host` | Ingress host | `cancer-genomics.yourdomain.com` |
| `ingress.tls[0].secretName` | TLS secret name | `cancer-genomics-tls` |

### Monitoring Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `monitoring.enabled` | Enable monitoring | `true` |
| `monitoring.serviceMonitor.enabled` | Enable ServiceMonitor | `true` |
| `monitoring.prometheusRule.enabled` | Enable PrometheusRule | `true` |

### Autoscaling Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `autoscaling.enabled` | Enable autoscaling | `false` |
| `autoscaling.minReplicas` | Minimum replicas | `2` |
| `autoscaling.maxReplicas` | Maximum replicas | `10` |
| `autoscaling.targetCPUUtilizationPercentage` | Target CPU utilization | `80` |

## Examples

### Basic Installation

```bash
helm install cancer-genomics ./helm/cancer-genomics-analysis-suite
```

### Production Installation

```bash
helm install cancer-genomics ./helm/cancer-genomics-analysis-suite \
  --set image.tag=v1.0.0 \
  --set web.replicaCount=5 \
  --set celery.worker.replicaCount=3 \
  --set postgresql.auth.password=secure-password \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=cancer-genomics.example.com \
  --set monitoring.enabled=true \
  --set autoscaling.enabled=true
```

### Development Installation

```bash
helm install cancer-genomics ./helm/cancer-genomics-analysis-suite \
  --set config.app.environment=development \
  --set config.app.debug=true \
  --set web.replicaCount=1 \
  --set celery.worker.replicaCount=1 \
  --set postgresql.primary.persistence.enabled=false \
  --set redis.master.persistence.enabled=false
```

### External Database

```bash
helm install cancer-genomics ./helm/cancer-genomics-analysis-suite \
  --set postgresql.enabled=false \
  --set config.database.host=external-postgres.example.com \
  --set config.database.port=5432 \
  --set config.database.name=genomics_db \
  --set config.database.user=postgres \
  --set config.database.password=secure-password
```

### Custom Image Registry

```bash
helm install cancer-genomics ./helm/cancer-genomics-analysis-suite \
  --set image.registry=your-registry.com \
  --set image.repository=your-org/cancer-genomics-analysis-suite \
  --set image.tag=v1.0.0
```

## Upgrading

To upgrade the chart:

```bash
helm upgrade cancer-genomics ./helm/cancer-genomics-analysis-suite
```

## Rollback

To rollback to a previous version:

```bash
helm rollback cancer-genomics
```

## Testing

To run the test suite:

```bash
helm test cancer-genomics
```

## Troubleshooting

### Common Issues

1. **Pod not starting**
   - Check pod logs: `kubectl logs -f deployment/cancer-genomics-web`
   - Verify image exists and is accessible
   - Check resource limits and requests

2. **Database connection issues**
   - Verify PostgreSQL is running: `kubectl get pods -l app=postgresql`
   - Check database credentials in secrets
   - Verify network connectivity

3. **Redis connection issues**
   - Verify Redis is running: `kubectl get pods -l app=redis`
   - Check Redis configuration
   - Verify network connectivity

4. **Ingress not working**
   - Check ingress controller is installed
   - Verify ingress configuration
   - Check DNS resolution

### Debug Commands

```bash
# Check pod status
kubectl get pods -l app=cancer-genomics-analysis-suite

# Check service status
kubectl get services -l app=cancer-genomics-analysis-suite

# Check ingress status
kubectl get ingress -l app=cancer-genomics-analysis-suite

# Check logs
kubectl logs -f deployment/cancer-genomics-web

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp

# Describe resources
kubectl describe pod <pod-name>
kubectl describe service <service-name>
kubectl describe ingress <ingress-name>
```

## Security Considerations

### Secrets Management

- Change default passwords in production
- Use Kubernetes secrets for sensitive data
- Consider using external secret management systems

### Network Security

- Enable network policies
- Use TLS for all communications
- Restrict ingress access

### Pod Security

- Run containers as non-root users
- Use read-only root filesystems where possible
- Implement security contexts

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test the chart
5. Submit a pull request

## License

This chart is licensed under the MIT License.
