# GKE Cluster Outputs
output "gke_cluster_id" {
  description = "GKE cluster ID"
  value       = google_container_cluster.main.id
}

output "gke_cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.main.name
}

output "gke_cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.main.endpoint
  sensitive   = true
}

output "gke_cluster_ca_certificate" {
  description = "GKE cluster CA certificate"
  value       = google_container_cluster.main.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "gke_cluster_location" {
  description = "GKE cluster location"
  value       = google_container_cluster.main.location
}

output "gke_cluster_network" {
  description = "GKE cluster network"
  value       = google_container_cluster.main.network
}

output "gke_cluster_subnetwork" {
  description = "GKE cluster subnetwork"
  value       = google_container_cluster.main.subnetwork
}

# VPC Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = google_compute_network.main.id
}

output "vpc_name" {
  description = "VPC name"
  value       = google_compute_network.main.name
}

output "vpc_self_link" {
  description = "VPC self link"
  value       = google_compute_network.main.self_link
}

output "private_subnet_id" {
  description = "Private subnet ID"
  value       = google_compute_subnetwork.private.id
}

output "private_subnet_name" {
  description = "Private subnet name"
  value       = google_compute_subnetwork.private.name
}

output "public_subnet_id" {
  description = "Public subnet ID"
  value       = google_compute_subnetwork.public.id
}

output "public_subnet_name" {
  description = "Public subnet name"
  value       = google_compute_subnetwork.public.name
}

# Cloud SQL Outputs
output "cloud_sql_instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.postgres.name
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.postgres.connection_name
}

output "cloud_sql_private_ip" {
  description = "Cloud SQL private IP"
  value       = google_sql_database_instance.postgres.private_ip_address
  sensitive   = true
}

output "cloud_sql_public_ip" {
  description = "Cloud SQL public IP"
  value       = google_sql_database_instance.postgres.public_ip_address
  sensitive   = true
}

output "cloud_sql_database_name" {
  description = "Cloud SQL database name"
  value       = google_sql_database.genomics.name
}

output "cloud_sql_username" {
  description = "Cloud SQL username"
  value       = google_sql_user.postgres.name
}

# Redis Outputs
output "redis_instance_name" {
  description = "Redis instance name"
  value       = google_redis_instance.redis.name
}

output "redis_host" {
  description = "Redis host"
  value       = google_redis_instance.redis.host
  sensitive   = true
}

output "redis_port" {
  description = "Redis port"
  value       = google_redis_instance.redis.port
}

output "redis_memory_size_gb" {
  description = "Redis memory size in GB"
  value       = google_redis_instance.redis.memory_size_gb
}

# Cloud Storage Outputs
output "storage_data_bucket" {
  description = "Storage data bucket name"
  value       = google_storage_bucket.data.name
}

output "storage_data_bucket_url" {
  description = "Storage data bucket URL"
  value       = google_storage_bucket.data.url
}

output "storage_artifacts_bucket" {
  description = "Storage artifacts bucket name"
  value       = google_storage_bucket.artifacts.name
}

output "storage_artifacts_bucket_url" {
  description = "Storage artifacts bucket URL"
  value       = google_storage_bucket.artifacts.url
}

output "storage_backups_bucket" {
  description = "Storage backups bucket name"
  value       = google_storage_bucket.backups.name
}

output "storage_backups_bucket_url" {
  description = "Storage backups bucket URL"
  value       = google_storage_bucket.backups.url
}

# Secret Manager Outputs
output "secret_manager_database_secret_id" {
  description = "Secret Manager database secret ID"
  value       = google_secret_manager_secret.database.secret_id
}

output "secret_manager_redis_secret_id" {
  description = "Secret Manager Redis secret ID"
  value       = google_secret_manager_secret.redis.secret_id
}

output "secret_manager_app_secret_id" {
  description = "Secret Manager app secret ID"
  value       = google_secret_manager_secret.app.secret_id
}

# Service Account Outputs
output "gke_service_account_email" {
  description = "GKE service account email"
  value       = google_service_account.gke_service_account.email
}

output "gke_service_account_name" {
  description = "GKE service account name"
  value       = google_service_account.gke_service_account.name
}

# Load Balancer Outputs
output "load_balancer_ip" {
  description = "Load balancer IP address"
  value       = google_compute_global_address.main.address
}

output "load_balancer_url" {
  description = "Load balancer URL"
  value       = "https://${google_compute_global_address.main.address}"
}

# DNS Outputs
output "dns_zone_name" {
  description = "DNS zone name"
  value       = var.domain_name != "" ? google_dns_managed_zone.main[0].name : null
}

output "dns_zone_dns_name" {
  description = "DNS zone DNS name"
  value       = var.domain_name != "" ? google_dns_managed_zone.main[0].dns_name : null
}

output "dns_name_servers" {
  description = "DNS name servers"
  value       = var.domain_name != "" ? google_dns_managed_zone.main[0].name_servers : null
}

# SSL Certificate Outputs
output "ssl_certificate_name" {
  description = "SSL certificate name"
  value       = var.domain_name != "" ? google_compute_managed_ssl_certificate.main[0].name : null
}

output "ssl_certificate_id" {
  description = "SSL certificate ID"
  value       = var.domain_name != "" ? google_compute_managed_ssl_certificate.main[0].id : null
}

# KMS Outputs
output "kms_key_ring_name" {
  description = "KMS key ring name"
  value       = google_kms_key_ring.bucket_encryption.name
}

output "kms_crypto_key_name" {
  description = "KMS crypto key name"
  value       = google_kms_crypto_key.bucket_encryption.name
}

output "kms_crypto_key_id" {
  description = "KMS crypto key ID"
  value       = google_kms_crypto_key.bucket_encryption.id
}

# Monitoring Outputs
output "monitoring_notification_channel_id" {
  description = "Monitoring notification channel ID"
  value       = var.alert_email != "" ? google_monitoring_notification_channel.email[0].id : null
}

output "monitoring_alert_policy_ids" {
  description = "Monitoring alert policy IDs"
  value = {
    high_cpu    = google_monitoring_alert_policy.high_cpu.id
    high_memory = google_monitoring_alert_policy.high_memory.id
  }
}

# Logging Outputs
output "logging_sink_name" {
  description = "Logging sink name"
  value       = google_logging_project_sink.main.name
}

output "logging_sink_destination" {
  description = "Logging sink destination"
  value       = google_logging_project_sink.main.destination
}

# Connection Information
output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.main.name} --region ${var.gcp_region} --project ${var.gcp_project_id}"
}

output "helm_install_command" {
  description = "Command to install the Helm chart"
  value       = "helm install cancer-genomics ./helm/cancer-genomics-analysis-suite --namespace ${var.kubernetes_namespace} --create-namespace"
}

# Environment Information
output "environment_info" {
  description = "Environment information"
  value = {
    project_name       = var.project_name
    environment        = var.environment
    gcp_project_id     = var.gcp_project_id
    gcp_region         = var.gcp_region
    domain_name        = var.domain_name
    kubernetes_version = var.kubernetes_version
    namespace          = var.kubernetes_namespace
  }
}

# Resource URLs
output "application_url" {
  description = "Application URL"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "https://${google_compute_global_address.main.address}"
}

output "grafana_url" {
  description = "Grafana URL (if enabled)"
  value       = var.domain_name != "" ? "https://grafana.${var.domain_name}" : "https://${google_compute_global_address.main.address}/grafana"
}

output "prometheus_url" {
  description = "Prometheus URL (if enabled)"
  value       = var.domain_name != "" ? "https://prometheus.${var.domain_name}" : "https://${google_compute_global_address.main.address}/prometheus"
}

# Cost Information
output "estimated_monthly_cost" {
  description = "Estimated monthly cost breakdown"
  value = {
    gke_cluster        = "~$150/month (3 e2-medium nodes)"
    cloud_sql_postgres = "~$100/month (db-standard-2)"
    redis_cluster      = "~$50/month (4GB STANDARD_HA)"
    load_balancer      = "~$20/month"
    cloud_storage      = "~$10/month (estimated)"
    total_estimated    = "~$330/month"
  }
}

# Security Information
output "security_recommendations" {
  description = "Security recommendations"
  value = [
    "Enable Cloud Security Command Center for security monitoring",
    "Set up Cloud Armor for DDoS protection and WAF",
    "Configure Cloud Identity and Access Management (IAM)",
    "Enable VPC Flow Logs for network monitoring",
    "Set up Cloud Audit Logs for compliance",
    "Configure Binary Authorization for container security",
    "Enable Shielded GKE nodes for enhanced security",
    "Set up Secret Manager for secrets management",
    "Configure Cloud KMS for encryption key management",
    "Enable Cloud Monitoring and Alerting"
  ]
}

# Monitoring Information
output "monitoring_setup" {
  description = "Monitoring setup information"
  value = {
    cloud_monitoring = var.enable_cloud_monitoring ? "Enabled" : "Disabled"
    cloud_logging    = var.enable_cloud_logging ? "Enabled" : "Disabled"
    cloud_trace      = var.enable_cloud_trace ? "Enabled" : "Disabled"
    cloud_profiler   = var.enable_cloud_profiler ? "Enabled" : "Disabled"
    error_reporting  = var.enable_error_reporting ? "Enabled" : "Disabled"
  }
}

# Backup Information
output "backup_configuration" {
  description = "Backup configuration"
  value = {
    cloud_sql_backup_retention = "${var.backup_retention_days} days"
    redis_backup_enabled       = var.redis_tier == "STANDARD_HA" ? "Yes" : "No"
    storage_versioning         = "Enabled"
    cross_region_backup        = var.enable_cross_region_backup ? "Enabled" : "Disabled"
    backup_schedule           = var.backup_schedule
  }
}

# Network Information
output "network_configuration" {
  description = "Network configuration"
  value = {
    vpc_name           = google_compute_network.main.name
    private_subnet     = google_compute_subnetwork.private.name
    public_subnet      = google_compute_subnetwork.public.name
    private_cluster    = var.enable_private_cluster
    network_policy     = var.enable_network_policy
    workload_identity  = var.enable_workload_identity
    binary_authorization = var.enable_binary_authorization
  }
}

# Compliance Information
output "compliance_status" {
  description = "Compliance status"
  value = {
    encryption_at_rest    = var.enable_encryption ? "Enabled" : "Disabled"
    encryption_in_transit = var.enable_data_encryption_in_transit ? "Enabled" : "Disabled"
    audit_logging         = var.enable_audit_logging ? "Enabled" : "Disabled"
    multi_az              = var.enable_multi_az ? "Enabled" : "Disabled"
    backup_enabled        = var.enable_backup ? "Enabled" : "Disabled"
    compliance_framework  = var.compliance_framework != "" ? var.compliance_framework : "Not specified"
    shielded_nodes        = var.enable_shielded_nodes ? "Enabled" : "Disabled"
    secure_boot           = var.enable_secure_boot ? "Enabled" : "Disabled"
    integrity_monitoring  = var.enable_integrity_monitoring ? "Enabled" : "Disabled"
  }
}

# Node Pool Information
output "node_pools" {
  description = "Node pool information"
  value = {
    general = {
      name         = google_container_node_pool.general.name
      machine_type = google_container_node_pool.general.node_config[0].machine_type
      disk_size_gb = google_container_node_pool.general.node_config[0].disk_size_gb
      min_nodes    = google_container_node_pool.general.autoscaling[0].min_node_count
      max_nodes    = google_container_node_pool.general.autoscaling[0].max_node_count
    }
    compute = {
      name         = google_container_node_pool.compute.name
      machine_type = google_container_node_pool.compute.node_config[0].machine_type
      disk_size_gb = google_container_node_pool.compute.node_config[0].disk_size_gb
      min_nodes    = google_container_node_pool.compute.autoscaling[0].min_node_count
      max_nodes    = google_container_node_pool.compute.autoscaling[0].max_node_count
      preemptible  = google_container_node_pool.compute.node_config[0].preemptible
    }
    storage = {
      name         = google_container_node_pool.storage.name
      machine_type = google_container_node_pool.storage.node_config[0].machine_type
      disk_size_gb = google_container_node_pool.storage.node_config[0].disk_size_gb
      min_nodes    = google_container_node_pool.storage.autoscaling[0].min_node_count
      max_nodes    = google_container_node_pool.storage.autoscaling[0].max_node_count
    }
  }
}

# Service Information
output "service_endpoints" {
  description = "Service endpoints"
  value = {
    gke_cluster = google_container_cluster.main.endpoint
    cloud_sql   = google_sql_database_instance.postgres.private_ip_address
    redis       = google_redis_instance.redis.host
    load_balancer = google_compute_global_address.main.address
  }
  sensitive = true
}

# Resource Limits
output "resource_limits" {
  description = "Resource limits and quotas"
  value = {
    max_nodes_per_pool = var.max_nodes_per_pool
    min_nodes_per_pool = var.min_nodes_per_pool
    cloud_sql_disk_size = var.cloud_sql_disk_size
    redis_memory_size_gb = var.redis_memory_size_gb
    storage_buckets = 3
    secret_manager_secrets = 3
  }
}

# Feature Flags
output "feature_flags" {
  description = "Feature flags status"
  value = {
    experimental_features = var.enable_experimental_features
    ai_ml_features       = var.enable_ai_ml_features
    real_time_processing = var.enable_real_time_processing
    gpu_nodes           = var.enable_gpu_nodes
    istio_service_mesh  = var.enable_istio
    cloud_cdn           = var.enable_cloud_cdn
    cloud_armor         = var.enable_cloud_armor
  }
}
