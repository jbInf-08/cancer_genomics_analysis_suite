# Outputs for Cancer Genomics Analysis Suite Infrastructure

# AWS Outputs
output "aws_eks_cluster_endpoint" {
  description = "Endpoint for EKS cluster"
  value       = var.environment == "prod" ? aws_eks_cluster.cancer_genomics[0].endpoint : null
}

output "aws_eks_cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = var.environment == "prod" ? aws_eks_cluster.cancer_genomics[0].vpc_config[0].cluster_security_group_id : null
}

output "aws_eks_cluster_arn" {
  description = "The Amazon Resource Name (ARN) of the cluster"
  value       = var.environment == "prod" ? aws_eks_cluster.cancer_genomics[0].arn : null
}

output "aws_eks_cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = var.environment == "prod" ? aws_eks_cluster.cancer_genomics[0].certificate_authority[0].data : null
}

output "aws_eks_cluster_name" {
  description = "The name of the EKS cluster"
  value       = var.environment == "prod" ? aws_eks_cluster.cancer_genomics[0].name : null
}

output "aws_eks_cluster_platform_version" {
  description = "Platform version for the EKS cluster"
  value       = var.environment == "prod" ? aws_eks_cluster.cancer_genomics[0].platform_version : null
}

output "aws_eks_cluster_status" {
  description = "Status of the EKS cluster"
  value       = var.environment == "prod" ? aws_eks_cluster.cancer_genomics[0].status : null
}

output "aws_eks_cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  value       = var.environment == "prod" ? aws_eks_cluster.cancer_genomics[0].version : null
}

output "aws_s3_bucket_name" {
  description = "Name of the S3 bucket for artifacts"
  value       = var.environment == "prod" && var.s3_bucket_name != "" ? aws_s3_bucket.artifacts[0].id : null
}

output "aws_s3_bucket_arn" {
  description = "ARN of the S3 bucket for artifacts"
  value       = var.environment == "prod" && var.s3_bucket_name != "" ? aws_s3_bucket.artifacts[0].arn : null
}

# GCP Outputs
output "gcp_gke_cluster_endpoint" {
  description = "Endpoint for GKE cluster"
  value       = var.environment == "prod" && var.gcp_project_id != "" ? google_container_cluster.cancer_genomics[0].endpoint : null
}

output "gcp_gke_cluster_name" {
  description = "Name of the GKE cluster"
  value       = var.environment == "prod" && var.gcp_project_id != "" ? google_container_cluster.cancer_genomics[0].name : null
}

output "gcp_gke_cluster_location" {
  description = "Location of the GKE cluster"
  value       = var.environment == "prod" && var.gcp_project_id != "" ? google_container_cluster.cancer_genomics[0].location : null
}

output "gcp_gke_cluster_ca_certificate" {
  description = "CA certificate for the GKE cluster"
  value       = var.environment == "prod" && var.gcp_project_id != "" ? google_container_cluster.cancer_genomics[0].master_auth[0].cluster_ca_certificate : null
}

output "gcp_gcs_bucket_name" {
  description = "Name of the GCS bucket for artifacts"
  value       = var.environment == "prod" && var.gcs_bucket_name != "" ? google_storage_bucket.artifacts[0].name : null
}

output "gcp_gcs_bucket_url" {
  description = "URL of the GCS bucket for artifacts"
  value       = var.environment == "prod" && var.gcs_bucket_name != "" ? google_storage_bucket.artifacts[0].url : null
}

# Kubernetes Outputs
output "kubernetes_namespace_name" {
  description = "Name of the Kubernetes namespace"
  value       = kubernetes_namespace.cancer_genomics.metadata[0].name
}

output "kubernetes_config_map_name" {
  description = "Name of the Kubernetes ConfigMap"
  value       = kubernetes_config_map.app_config.metadata[0].name
}

output "kubernetes_secret_name" {
  description = "Name of the Kubernetes Secret"
  value       = kubernetes_secret.app_secrets.metadata[0].name
}

# Helm Outputs
output "nginx_ingress_status" {
  description = "Status of the NGINX Ingress Controller"
  value       = helm_release.nginx_ingress.status
}

output "cert_manager_status" {
  description = "Status of the Cert-Manager"
  value       = helm_release.cert_manager.status
}

output "postgresql_status" {
  description = "Status of the PostgreSQL deployment"
  value       = helm_release.postgresql.status
}

output "redis_status" {
  description = "Status of the Redis deployment"
  value       = helm_release.redis.status
}

output "prometheus_status" {
  description = "Status of the Prometheus deployment"
  value       = var.enable_monitoring ? helm_release.prometheus[0].status : null
}

output "argocd_status" {
  description = "Status of the ArgoCD deployment"
  value       = var.enable_argocd ? helm_release.argocd[0].status : null
}

output "cancer_genomics_app_status" {
  description = "Status of the Cancer Genomics application"
  value       = helm_release.cancer_genomics_app.status
}

# Application URLs
output "application_url" {
  description = "URL of the main application"
  value       = "https://${var.domain_name}"
}

output "api_url" {
  description = "URL of the API"
  value       = "https://${var.api_domain_name}"
}

output "argocd_url" {
  description = "URL of ArgoCD (if enabled)"
  value       = var.enable_argocd ? "https://argocd.${var.domain_name}" : null
}

# Connection Information
output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = var.environment == "prod" ? (
    var.gcp_project_id != "" ? 
    "gcloud container clusters get-credentials ${google_container_cluster.cancer_genomics[0].name} --region ${var.gcp_region}" :
    "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.cancer_genomics[0].name}"
  ) : null
}

# Service Account Information
output "gcp_service_account_email" {
  description = "Email of the GCP service account"
  value       = var.environment == "prod" && var.gcp_project_id != "" ? google_service_account.gke_node[0].email : null
}

output "aws_iam_role_arn" {
  description = "ARN of the AWS IAM role"
  value       = var.environment == "prod" ? aws_iam_role.eks_node_group[0].arn : null
}
