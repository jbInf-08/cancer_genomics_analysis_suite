# Helm Charts for Cancer Genomics Analysis Suite

# NGINX Ingress Controller
resource "helm_release" "nginx_ingress" {
  name       = "nginx-ingress"
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  version    = "4.8.3"
  namespace  = "ingress-nginx"

  create_namespace = true

  values = [
    yamlencode({
      controller = {
        service = {
          type = "LoadBalancer"
          annotations = {
            "service.beta.kubernetes.io/aws-load-balancer-type" = "nlb"
            "service.beta.kubernetes.io/aws-load-balancer-backend-protocol" = "tcp"
          }
        }
        config = {
          "use-forwarded-headers" = "true"
          "compute-full-forwarded-for" = "true"
          "use-proxy-protocol" = "false"
        }
        metrics = {
          enabled = var.enable_monitoring
        }
        resources = {
          requests = {
            cpu    = "100m"
            memory = "128Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }
      }
    })
  ]

  depends_on = [kubernetes_namespace.cancer_genomics]
}

# Cert-Manager
resource "helm_release" "cert_manager" {
  name       = "cert-manager"
  repository = "https://charts.jetstack.io"
  chart      = "cert-manager"
  version    = "v1.13.0"
  namespace  = "cert-manager"

  create_namespace = true

  set {
    name  = "installCRDs"
    value = "true"
  }

  set {
    name  = "global.leaderElection.namespace"
    value = "cert-manager"
  }

  values = [
    yamlencode({
      resources = {
        requests = {
          cpu    = "100m"
          memory = "128Mi"
        }
        limits = {
          cpu    = "500m"
          memory = "512Mi"
        }
      }
      webhook = {
        resources = {
          requests = {
            cpu    = "100m"
            memory = "128Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }
      }
      cainjector = {
        resources = {
          requests = {
            cpu    = "100m"
            memory = "128Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }
      }
    })
  ]

  depends_on = [kubernetes_namespace.cancer_genomics]
}

# PostgreSQL
resource "helm_release" "postgresql" {
  name       = "postgresql"
  repository = "https://charts.bitnami.com/bitnami"
  chart      = "postgresql"
  version    = "12.12.0"
  namespace  = kubernetes_namespace.cancer_genomics.metadata[0].name

  values = [
    yamlencode({
      auth = {
        postgresPassword = "your-postgres-password" # Should be moved to secrets
        database = "cancer_genomics"
      }
      primary = {
        persistence = {
          enabled = true
          size = var.postgres_storage_size
        }
        resources = {
          requests = {
            cpu    = "250m"
            memory = "512Mi"
          }
          limits = {
            cpu    = "1000m"
            memory = "2Gi"
          }
        }
      }
      metrics = {
        enabled = var.enable_monitoring
      }
    })
  ]

  depends_on = [kubernetes_namespace.cancer_genomics]
}

# Redis
resource "helm_release" "redis" {
  name       = "redis"
  repository = "https://charts.bitnami.com/bitnami"
  chart      = "redis"
  version    = "17.11.0"
  namespace  = kubernetes_namespace.cancer_genomics.metadata[0].name

  values = [
    yamlencode({
      auth = {
        enabled = true
        password = "your-redis-password" # Should be moved to secrets
      }
      master = {
        persistence = {
          enabled = true
          size = var.redis_storage_size
        }
        resources = {
          requests = {
            cpu    = "100m"
            memory = "128Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }
      }
      replica = {
        replicaCount = 1
        persistence = {
          enabled = true
          size = var.redis_storage_size
        }
        resources = {
          requests = {
            cpu    = "100m"
            memory = "128Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }
      }
      metrics = {
        enabled = var.enable_monitoring
      }
    })
  ]

  depends_on = [kubernetes_namespace.cancer_genomics]
}

# Prometheus (if monitoring is enabled)
resource "helm_release" "prometheus" {
  count = var.enable_monitoring ? 1 : 0

  name       = "prometheus"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = "51.0.0"
  namespace  = "monitoring"

  create_namespace = true

  values = [
    yamlencode({
      prometheus = {
        prometheusSpec = {
          resources = {
            requests = {
              cpu    = "200m"
              memory = "512Mi"
            }
            limits = {
              cpu    = "1000m"
              memory = "2Gi"
            }
          }
          storageSpec = {
            volumeClaimTemplate = {
              spec = {
                storageClassName = "gp2"
                accessModes = ["ReadWriteOnce"]
                resources = {
                  requests = {
                    storage = "50Gi"
                  }
                }
              }
            }
          }
        }
      }
      grafana = {
        enabled = true
        resources = {
          requests = {
            cpu    = "100m"
            memory = "128Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }
        persistence = {
          enabled = true
          size = "10Gi"
        }
      }
      alertmanager = {
        alertmanagerSpec = {
          resources = {
            requests = {
              cpu    = "100m"
              memory = "128Mi"
            }
            limits = {
              cpu    = "500m"
              memory = "512Mi"
            }
          }
        }
      }
    })
  ]

  depends_on = [kubernetes_namespace.cancer_genomics]
}

# ArgoCD (if enabled)
resource "helm_release" "argocd" {
  count = var.enable_argocd ? 1 : 0

  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = "5.46.0"
  namespace  = "argocd"

  create_namespace = true

  values = [
    yamlencode({
      global = {
        domain = "argocd.${var.domain_name}"
      }
      server = {
        service = {
          type = "LoadBalancer"
        }
        ingress = {
          enabled = true
          ingressClassName = "nginx"
          annotations = {
            "cert-manager.io/cluster-issuer" = "letsencrypt-prod"
            "nginx.ingress.kubernetes.io/ssl-redirect" = "true"
            "nginx.ingress.kubernetes.io/force-ssl-redirect" = "true"
          }
          hosts = ["argocd.${var.domain_name}"]
          tls = [{
            secretName = "argocd-tls"
            hosts = ["argocd.${var.domain_name}"]
          }]
        }
        resources = {
          requests = {
            cpu    = "100m"
            memory = "128Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }
      }
      controller = {
        resources = {
          requests = {
            cpu    = "100m"
            memory = "128Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }
      }
      repoServer = {
        resources = {
          requests = {
            cpu    = "100m"
            memory = "128Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }
      }
      applicationSet = {
        resources = {
          requests = {
            cpu    = "100m"
            memory = "128Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }
      }
    })
  ]

  depends_on = [helm_release.nginx_ingress, helm_release.cert_manager]
}

# Cancer Genomics Application
resource "helm_release" "cancer_genomics_app" {
  name       = "cancer-genomics-analysis-suite"
  chart      = "./helm/cancer-genomics-analysis-suite"
  namespace  = kubernetes_namespace.cancer_genomics.metadata[0].name

  values = [
    yamlencode({
      global = {
        domain = var.domain_name
        apiDomain = var.api_domain_name
      }
      
      ingress = {
        enabled = true
        className = "nginx"
        annotations = {
          "cert-manager.io/cluster-issuer" = "letsencrypt-prod"
          "nginx.ingress.kubernetes.io/ssl-redirect" = "true"
          "nginx.ingress.kubernetes.io/force-ssl-redirect" = "true"
        }
        hosts = [
          {
            host = var.domain_name
            paths = [
              {
                path = "/"
                pathType = "Prefix"
              }
            ]
          }
        ]
        tls = [
          {
            secretName = "cancer-genomics-tls"
            hosts = [var.domain_name]
          }
        ]
      }
      
      apiIngress = {
        enabled = true
        className = "nginx"
        annotations = {
          "cert-manager.io/cluster-issuer" = "letsencrypt-prod"
          "nginx.ingress.kubernetes.io/ssl-redirect" = "true"
          "nginx.ingress.kubernetes.io/force-ssl-redirect" = "true"
        }
        hosts = [
          {
            host = var.api_domain_name
            paths = [
              {
                path = "/"
                pathType = "Prefix"
              }
            ]
          }
        ]
        tls = [
          {
            secretName = "cancer-genomics-api-tls"
            hosts = [var.api_domain_name]
          }
        ]
      }
      
      app = {
        resources = {
          requests = {
            cpu = var.cpu_request
            memory = var.memory_request
          }
          limits = {
            cpu = var.cpu_limit
            memory = var.memory_limit
          }
        }
      }
      
      postgresql = {
        enabled = false # Using separate PostgreSQL deployment
      }
      
      redis = {
        enabled = false # Using separate Redis deployment
      }
      
      monitoring = {
        enabled = var.enable_monitoring
      }
    })
  ]

  depends_on = [
    helm_release.nginx_ingress,
    helm_release.cert_manager,
    helm_release.postgresql,
    helm_release.redis
  ]
}
