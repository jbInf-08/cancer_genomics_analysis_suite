# EKS Cluster Outputs
output "eks_cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "eks_cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = module.eks.cluster_security_group_id
}

output "eks_cluster_oidc_issuer_url" {
  description = "EKS cluster OIDC issuer URL"
  value       = module.eks.cluster_oidc_issuer_url
}

output "eks_cluster_certificate_authority_data" {
  description = "EKS cluster certificate authority data"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "eks_oidc_provider_arn" {
  description = "EKS OIDC provider ARN"
  value       = module.eks.oidc_provider_arn
}

# VPC Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

output "database_subnets" {
  description = "Database subnet IDs"
  value       = module.vpc.database_subnets
}

output "nat_gateway_ids" {
  description = "NAT Gateway IDs"
  value       = module.vpc.natgw_ids
}

# RDS Outputs
output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.db_instance_endpoint
  sensitive   = true
}

output "rds_port" {
  description = "RDS port"
  value       = module.rds.db_instance_port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.rds.db_instance_name
}

output "rds_username" {
  description = "RDS username"
  value       = module.rds.db_instance_username
}

output "rds_arn" {
  description = "RDS instance ARN"
  value       = module.rds.db_instance_arn
}

# Redis Outputs
output "redis_endpoint" {
  description = "Redis endpoint"
  value       = aws_elasticache_replication_group.redis.configuration_endpoint_address
  sensitive   = true
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.redis.port
}

output "redis_arn" {
  description = "Redis replication group ARN"
  value       = aws_elasticache_replication_group.redis.arn
}

# S3 Outputs
output "s3_data_bucket" {
  description = "S3 data bucket name"
  value       = aws_s3_bucket.data.bucket
}

output "s3_data_bucket_arn" {
  description = "S3 data bucket ARN"
  value       = aws_s3_bucket.data.arn
}

output "s3_artifacts_bucket" {
  description = "S3 artifacts bucket name"
  value       = aws_s3_bucket.artifacts.bucket
}

output "s3_artifacts_bucket_arn" {
  description = "S3 artifacts bucket ARN"
  value       = aws_s3_bucket.artifacts.arn
}

output "s3_backups_bucket" {
  description = "S3 backups bucket name"
  value       = aws_s3_bucket.backups.bucket
}

output "s3_backups_bucket_arn" {
  description = "S3 backups bucket ARN"
  value       = aws_s3_bucket.backups.arn
}

# Secrets Manager Outputs
output "secrets_manager_database_arn" {
  description = "Secrets Manager database secret ARN"
  value       = aws_secretsmanager_secret.database.arn
}

output "secrets_manager_redis_arn" {
  description = "Secrets Manager Redis secret ARN"
  value       = aws_secretsmanager_secret.redis.arn
}

output "secrets_manager_app_arn" {
  description = "Secrets Manager app secret ARN"
  value       = aws_secretsmanager_secret.app.arn
}

# IAM Outputs
output "eks_service_account_role_arn" {
  description = "EKS service account role ARN"
  value       = aws_iam_role.eks_service_account.arn
}

output "eks_admin_role_arn" {
  description = "EKS admin role ARN"
  value       = aws_iam_role.eks_admin.arn
}

# Load Balancer Outputs
output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Application Load Balancer zone ID"
  value       = aws_lb.main.zone_id
}

output "alb_arn" {
  description = "Application Load Balancer ARN"
  value       = aws_lb.main.arn
}

output "alb_target_group_arn" {
  description = "Application Load Balancer target group ARN"
  value       = aws_lb_target_group.main.arn
}

# Route 53 Outputs
output "route53_zone_id" {
  description = "Route 53 hosted zone ID"
  value       = var.domain_name != "" ? aws_route53_zone.main[0].zone_id : null
}

output "route53_name_servers" {
  description = "Route 53 name servers"
  value       = var.domain_name != "" ? aws_route53_zone.main[0].name_servers : null
}

# ACM Certificate Outputs
output "acm_certificate_arn" {
  description = "ACM certificate ARN"
  value       = var.domain_name != "" ? aws_acm_certificate.main[0].arn : null
}

output "acm_certificate_domain_name" {
  description = "ACM certificate domain name"
  value       = var.domain_name != "" ? aws_acm_certificate.main[0].domain_name : null
}

# Security Group Outputs
output "alb_security_group_id" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

output "redis_security_group_id" {
  description = "Redis security group ID"
  value       = aws_security_group.redis.id
}

# CloudWatch Outputs
output "cloudwatch_log_group_eks" {
  description = "CloudWatch log group for EKS"
  value       = aws_cloudwatch_log_group.eks.name
}

output "cloudwatch_log_group_application" {
  description = "CloudWatch log group for application"
  value       = aws_cloudwatch_log_group.application.name
}

# DynamoDB Outputs
output "dynamodb_terraform_locks_table" {
  description = "DynamoDB table for Terraform state locking"
  value       = aws_dynamodb_table.terraform_locks.name
}

output "dynamodb_terraform_locks_arn" {
  description = "DynamoDB table ARN for Terraform state locking"
  value       = aws_dynamodb_table.terraform_locks.arn
}

# Connection Information
output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_id}"
}

output "helm_install_command" {
  description = "Command to install the Helm chart"
  value       = "helm install cancer-genomics ./helm/cancer-genomics-analysis-suite --namespace ${var.kubernetes_namespace} --create-namespace"
}

# Environment Information
output "environment_info" {
  description = "Environment information"
  value = {
    project_name    = var.project_name
    environment     = var.environment
    aws_region      = var.aws_region
    domain_name     = var.domain_name
    kubernetes_version = var.kubernetes_version
    namespace       = var.kubernetes_namespace
  }
}

# Resource URLs
output "application_url" {
  description = "Application URL"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"
}

output "grafana_url" {
  description = "Grafana URL (if enabled)"
  value       = var.domain_name != "" ? "https://grafana.${var.domain_name}" : "http://${aws_lb.main.dns_name}/grafana"
}

output "prometheus_url" {
  description = "Prometheus URL (if enabled)"
  value       = var.domain_name != "" ? "https://prometheus.${var.domain_name}" : "http://${aws_lb.main.dns_name}/prometheus"
}

# Cost Information
output "estimated_monthly_cost" {
  description = "Estimated monthly cost breakdown"
  value = {
    eks_cluster     = "~$73/month (3 t3.medium nodes)"
    rds_postgresql  = "~$50/month (db.t3.medium)"
    redis_cluster   = "~$30/month (2 cache.t3.medium nodes)"
    alb             = "~$20/month"
    nat_gateway     = "~$45/month (3 NAT gateways)"
    s3_storage      = "~$10/month (estimated)"
    total_estimated = "~$228/month"
  }
}

# Security Information
output "security_recommendations" {
  description = "Security recommendations"
  value = [
    "Enable AWS Config for compliance monitoring",
    "Set up AWS GuardDuty for threat detection",
    "Configure AWS Security Hub for security findings",
    "Enable VPC Flow Logs for network monitoring",
    "Set up AWS CloudTrail for API auditing",
    "Configure AWS WAF for web application protection",
    "Enable AWS Shield for DDoS protection",
    "Set up AWS Secrets Manager rotation",
    "Configure AWS Backup for disaster recovery",
    "Enable AWS CloudWatch Container Insights"
  ]
}

# Monitoring Information
output "monitoring_setup" {
  description = "Monitoring setup information"
  value = {
    cloudwatch_logs = "Enabled with ${var.log_retention_days} days retention"
    container_insights = var.enable_cloudwatch_insights ? "Enabled" : "Disabled"
    xray_tracing = var.enable_xray_tracing ? "Enabled" : "Disabled"
    enhanced_monitoring = var.enable_enhanced_monitoring ? "Enabled" : "Disabled"
    performance_insights = var.enable_performance_insights ? "Enabled" : "Disabled"
  }
}

# Backup Information
output "backup_configuration" {
  description = "Backup configuration"
  value = {
    rds_backup_retention = "${var.backup_retention_days} days"
    redis_backup_enabled = var.environment == "production" ? "Yes" : "No"
    s3_versioning = "Enabled"
    cross_region_backup = var.enable_cross_region_backup ? "Enabled" : "Disabled"
    backup_schedule = var.backup_schedule
  }
}

# Network Information
output "network_configuration" {
  description = "Network configuration"
  value = {
    vpc_cidr = local.vpc_cidr
    public_subnets = local.public_subnet_cidrs
    private_subnets = local.private_subnet_cidrs
    database_subnets = local.database_subnet_cidrs
    nat_gateway_enabled = var.enable_nat_gateway
    vpn_gateway_enabled = var.enable_vpn_gateway
    availability_zones = local.azs
  }
}

# Compliance Information
output "compliance_status" {
  description = "Compliance status"
  value = {
    encryption_at_rest = var.enable_encryption ? "Enabled" : "Disabled"
    encryption_in_transit = var.enable_data_encryption_in_transit ? "Enabled" : "Disabled"
    audit_logging = var.enable_audit_logging ? "Enabled" : "Disabled"
    multi_az = var.enable_multi_az ? "Enabled" : "Disabled"
    backup_enabled = var.enable_backup ? "Enabled" : "Disabled"
    compliance_framework = var.compliance_framework != "" ? var.compliance_framework : "Not specified"
  }
}
