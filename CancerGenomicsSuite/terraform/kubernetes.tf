# Kubernetes Resources for Cancer Genomics Analysis Suite

# Namespace
resource "kubernetes_namespace" "cancer_genomics" {
  metadata {
    name = "cancer-genomics"
    labels = {
      name = "cancer-genomics"
      app  = "cancer-genomics-analysis-suite"
    }
  }
}

# ConfigMap for application configuration
resource "kubernetes_config_map" "app_config" {
  metadata {
    name      = "cancer-genomics-config"
    namespace = kubernetes_namespace.cancer_genomics.metadata[0].name
  }

  data = {
    ENVIRONMENT = var.environment
    LOG_LEVEL   = var.environment == "prod" ? "INFO" : "DEBUG"
    
    # Database configuration
    POSTGRES_HOST     = "postgresql"
    POSTGRES_PORT     = "5432"
    POSTGRES_DB       = "cancer_genomics"
    POSTGRES_USER     = "postgres"
    
    # Redis configuration
    REDIS_HOST        = "redis"
    REDIS_PORT        = "6379"
    REDIS_DB          = "0"
    
    # Application configuration
    FLASK_ENV         = var.environment == "prod" ? "production" : "development"
    SECRET_KEY        = "your-secret-key-here" # Should be moved to secrets
    
    # Storage configuration
    S3_BUCKET_NAME    = var.s3_bucket_name != "" ? var.s3_bucket_name : ""
    GCS_BUCKET_NAME   = var.gcs_bucket_name != "" ? var.gcs_bucket_name : ""
    
    # Monitoring
    ENABLE_MONITORING = var.enable_monitoring ? "true" : "false"
    ENABLE_LOGGING    = var.enable_logging ? "true" : "false"
  }
}

# Secret for database credentials
resource "kubernetes_secret" "db_credentials" {
  metadata {
    name      = "db-credentials"
    namespace = kubernetes_namespace.cancer_genomics.metadata[0].name
  }

  data = {
    POSTGRES_PASSWORD = base64encode("your-postgres-password") # Should be moved to cloud secrets
    REDIS_PASSWORD    = base64encode("your-redis-password")    # Should be moved to cloud secrets
  }

  type = "Opaque"
}

# Secret for application secrets
resource "kubernetes_secret" "app_secrets" {
  metadata {
    name      = "app-secrets"
    namespace = kubernetes_namespace.cancer_genomics.metadata[0].name
  }

  data = {
    SECRET_KEY = base64encode("your-secret-key-here") # Should be moved to cloud secrets
  }

  type = "Opaque"
}

# Service Account
resource "kubernetes_service_account" "cancer_genomics" {
  metadata {
    name      = "cancer-genomics-sa"
    namespace = kubernetes_namespace.cancer_genomics.metadata[0].name
  }

  automount_service_account_token = true
}

# ClusterRole for application
resource "kubernetes_cluster_role" "cancer_genomics" {
  metadata {
    name = "cancer-genomics-role"
  }

  rule {
    api_groups = [""]
    resources  = ["pods", "services", "configmaps", "secrets"]
    verbs      = ["get", "list", "watch"]
  }

  rule {
    api_groups = ["apps"]
    resources  = ["deployments", "replicasets"]
    verbs      = ["get", "list", "watch"]
  }

  rule {
    api_groups = ["networking.k8s.io"]
    resources  = ["ingresses"]
    verbs      = ["get", "list", "watch"]
  }
}

# ClusterRoleBinding
resource "kubernetes_cluster_role_binding" "cancer_genomics" {
  metadata {
    name = "cancer-genomics-binding"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.cancer_genomics.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.cancer_genomics.metadata[0].name
    namespace = kubernetes_namespace.cancer_genomics.metadata[0].name
  }
}

# Network Policy
resource "kubernetes_network_policy" "cancer_genomics" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "cancer-genomics-netpol"
    namespace = kubernetes_namespace.cancer_genomics.metadata[0].name
  }

  spec {
    pod_selector {
      match_labels = {
        app = "cancer-genomics-analysis-suite"
      }
    }

    policy_types = ["Ingress", "Egress"]

    ingress {
      from {
        namespace_selector {
          match_labels = {
            name = "cancer-genomics"
          }
        }
      }
    }

    ingress {
      ports {
        port     = "8050"
        protocol = "TCP"
      }
    }

    egress {
      to {
        namespace_selector {
          match_labels = {
            name = "cancer-genomics"
          }
        }
      }
    }

    egress {
      ports {
        port     = "5432"
        protocol = "TCP"
      }
    }

    egress {
      ports {
        port     = "6379"
        protocol = "TCP"
      }
    }

    egress {
      ports {
        port     = "443"
        protocol = "TCP"
      }
    }

    egress {
      ports {
        port     = "80"
        protocol = "TCP"
      }
    }
  }
}

# Pod Security Policy
resource "kubernetes_pod_security_policy" "cancer_genomics" {
  count = var.enable_pod_security_policies ? 1 : 0

  metadata {
    name = "cancer-genomics-psp"
  }

  spec {
    privileged                 = false
    allow_privilege_escalation = false
    required_drop_capabilities = ["ALL"]
    volumes = [
      "configMap",
      "emptyDir",
      "projected",
      "secret",
      "downwardAPI",
      "persistentVolumeClaim"
    ]

    run_as_user {
      rule = "MustRunAsNonRoot"
    }

    se_linux {
      rule = "RunAsAny"
    }

    fs_group {
      rule = "RunAsAny"
    }
  }
}

# Role for Pod Security Policy
resource "kubernetes_cluster_role" "cancer_genomics_psp" {
  count = var.enable_pod_security_policies ? 1 : 0

  metadata {
    name = "cancer-genomics-psp-role"
  }

  rule {
    api_groups     = ["policy"]
    resources      = ["podsecuritypolicies"]
    verbs          = ["use"]
    resource_names = [kubernetes_pod_security_policy.cancer_genomics[0].metadata[0].name]
  }
}

# RoleBinding for Pod Security Policy
resource "kubernetes_cluster_role_binding" "cancer_genomics_psp" {
  count = var.enable_pod_security_policies ? 1 : 0

  metadata {
    name = "cancer-genomics-psp-binding"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.cancer_genomics_psp[0].metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.cancer_genomics.metadata[0].name
    namespace = kubernetes_namespace.cancer_genomics.metadata[0].name
  }
}

# Resource Quotas
resource "kubernetes_resource_quota" "cancer_genomics" {
  metadata {
    name      = "cancer-genomics-quota"
    namespace = kubernetes_namespace.cancer_genomics.metadata[0].name
  }

  spec {
    hard = {
      requests.cpu    = "4"
      requests.memory = "8Gi"
      limits.cpu      = "8"
      limits.memory   = "16Gi"
      pods            = "10"
      services        = "5"
      secrets         = "10"
      configmaps      = "10"
    }
  }
}

# Limit Range
resource "kubernetes_limit_range" "cancer_genomics" {
  metadata {
    name      = "cancer-genomics-limits"
    namespace = kubernetes_namespace.cancer_genomics.metadata[0].name
  }

  spec {
    limit {
      type = "Container"
      default = {
        cpu    = "500m"
        memory = "1Gi"
      }
      default_request = {
        cpu    = "100m"
        memory = "128Mi"
      }
      max = {
        cpu    = "2"
        memory = "4Gi"
      }
      min = {
        cpu    = "50m"
        memory = "64Mi"
      }
    }
  }
}
