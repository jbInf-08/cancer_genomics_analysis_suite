# Variables for Cancer Genomics Analysis Suite Infrastructure

# General Configuration
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "cancer-genomics-analysis-suite"
}

variable "kubeconfig_path" {
  description = "Path to kubeconfig file"
  type        = string
  default     = "~/.kube/config"
}

# AWS Configuration
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "aws_availability_zones" {
  description = "AWS availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b", "us-west-2c"]
}

variable "aws_instance_type" {
  description = "AWS EC2 instance type for EKS nodes"
  type        = string
  default     = "t3.medium"
}

variable "aws_node_count" {
  description = "Number of nodes in the EKS cluster"
  type        = number
  default     = 3
}

# GCP Configuration
variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
  default     = ""
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "gcp_zone" {
  description = "GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "gcp_machine_type" {
  description = "GCP machine type for GKE nodes"
  type        = string
  default     = "e2-standard-2"
}

variable "gcp_node_count" {
  description = "Number of nodes in the GKE cluster"
  type        = number
  default     = 3
}

# Domain Configuration
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "cancer-genomics.yourdomain.com"
}

variable "api_domain_name" {
  description = "API domain name"
  type        = string
  default     = "api.cancer-genomics.yourdomain.com"
}

# Database Configuration
variable "postgres_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "15"
}

variable "postgres_storage_size" {
  description = "PostgreSQL storage size"
  type        = string
  default     = "100Gi"
}

variable "redis_version" {
  description = "Redis version"
  type        = string
  default     = "7"
}

variable "redis_storage_size" {
  description = "Redis storage size"
  type        = string
  default     = "50Gi"
}

# Storage Configuration
variable "s3_bucket_name" {
  description = "S3 bucket name for artifacts"
  type        = string
  default     = ""
}

variable "gcs_bucket_name" {
  description = "GCS bucket name for artifacts"
  type        = string
  default     = ""
}

# Security Configuration
variable "enable_aws_secrets_manager" {
  description = "Enable AWS Secrets Manager integration"
  type        = bool
  default     = false
}

variable "enable_gcp_secret_manager" {
  description = "Enable GCP Secret Manager integration"
  type        = bool
  default     = false
}

variable "enable_network_policies" {
  description = "Enable Kubernetes network policies"
  type        = bool
  default     = true
}

variable "enable_pod_security_policies" {
  description = "Enable Pod Security Policies"
  type        = bool
  default     = true
}

# Monitoring Configuration
variable "enable_monitoring" {
  description = "Enable monitoring stack (Prometheus, Grafana)"
  type        = bool
  default     = true
}

variable "enable_logging" {
  description = "Enable centralized logging"
  type        = bool
  default     = true
}

# ArgoCD Configuration
variable "enable_argocd" {
  description = "Enable ArgoCD for GitOps"
  type        = bool
  default     = true
}

variable "argocd_repo_url" {
  description = "ArgoCD repository URL"
  type        = string
  default     = ""
}

variable "argocd_target_revision" {
  description = "ArgoCD target revision"
  type        = string
  default     = "HEAD"
}

# Resource Limits
variable "cpu_limit" {
  description = "CPU limit for main application"
  type        = string
  default     = "2000m"
}

variable "memory_limit" {
  description = "Memory limit for main application"
  type        = string
  default     = "4Gi"
}

variable "cpu_request" {
  description = "CPU request for main application"
  type        = string
  default     = "500m"
}

variable "memory_request" {
  description = "Memory request for main application"
  type        = string
  default     = "1Gi"
}
