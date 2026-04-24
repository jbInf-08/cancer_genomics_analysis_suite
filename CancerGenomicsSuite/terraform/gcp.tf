# GCP Infrastructure for Cancer Genomics Analysis Suite

# GKE Cluster
resource "google_container_cluster" "cancer_genomics" {
  count   = var.environment == "prod" && var.gcp_project_id != "" ? 1 : 0
  name    = "${var.project_name}-${var.environment}-${local.name_suffix}"
  location = var.gcp_region

  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.cancer_genomics[0].name
  subnetwork = google_compute_subnetwork.cancer_genomics[0].name

  # Enable network policy
  network_policy {
    enabled = var.enable_network_policies
  }

  # Enable pod security policy
  pod_security_policy_config {
    enabled = var.enable_pod_security_policies
  }

  # Enable workload identity
  workload_identity_config {
    workload_pool = "${var.gcp_project_id}.svc.id.goog"
  }

  # Enable private nodes
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  # Enable master authorized networks
  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "0.0.0.0/0"
      display_name = "All"
    }
  }

  # Enable binary authorization
  binary_authorization {
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }

  # Enable cluster autoscaling
  cluster_autoscaling {
    enabled = true
    resource_limits {
      resource_type = "cpu"
      minimum       = 1
      maximum       = 10
    }
    resource_limits {
      resource_type = "memory"
      minimum       = 1
      maximum       = 100
    }
  }

  depends_on = [
    google_project_service.container,
    google_project_service.compute,
  ]

  lifecycle {
    ignore_changes = [
      node_config,
    ]
  }
}

# GKE Node Pool
resource "google_container_node_pool" "cancer_genomics" {
  count      = var.environment == "prod" && var.gcp_project_id != "" ? 1 : 0
  name       = "${var.project_name}-node-pool-${local.name_suffix}"
  location   = var.gcp_region
  cluster    = google_container_cluster.cancer_genomics[0].name
  node_count = var.gcp_node_count

  node_config {
    preemptible  = false
    machine_type = var.gcp_machine_type

    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    service_account = google_service_account.gke_node[0].email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    # Enable workload identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    # Enable secure boot
    shielded_instance_config {
      enable_secure_boot = true
    }

    # Enable confidential nodes
    confidential_nodes {
      enabled = true
    }

    metadata = {
      disable-legacy-endpoints = "true"
    }

    labels = local.common_tags

    tags = ["gke-node", "${var.project_name}-${var.environment}"]
  }

  autoscaling {
    min_node_count = 1
    max_node_count = 10
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# VPC Network
resource "google_compute_network" "cancer_genomics" {
  count                 = var.environment == "prod" && var.gcp_project_id != "" ? 1 : 0
  name                  = "${var.project_name}-vpc-${local.name_suffix}"
  auto_create_subnetworks = false
  routing_mode          = "REGIONAL"
}

# Subnet
resource "google_compute_subnetwork" "cancer_genomics" {
  count         = var.environment == "prod" && var.gcp_project_id != "" ? 1 : 0
  name          = "${var.project_name}-subnet-${local.name_suffix}"
  ip_cidr_range = "10.0.0.0/16"
  region        = var.gcp_region
  network       = google_compute_network.cancer_genomics[0].id

  # Enable private Google access
  private_ip_google_access = true

  # Secondary IP ranges for pods and services
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/20"
  }
}

# Firewall Rules
resource "google_compute_firewall" "allow_ingress" {
  count = var.environment == "prod" && var.gcp_project_id != "" ? 1 : 0
  name  = "${var.project_name}-allow-ingress-${local.name_suffix}"
  network = google_compute_network.cancer_genomics[0].name

  allow {
    protocol = "tcp"
    ports    = ["80", "443", "8080", "8443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["gke-node", "${var.project_name}-${var.environment}"]
}

resource "google_compute_firewall" "allow_ssh" {
  count = var.environment == "prod" && var.gcp_project_id != "" ? 1 : 0
  name  = "${var.project_name}-allow-ssh-${local.name_suffix}"
  network = google_compute_network.cancer_genomics[0].name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["gke-node", "${var.project_name}-${var.environment}"]
}

# GCS Bucket for Artifacts
resource "google_storage_bucket" "artifacts" {
  count  = var.environment == "prod" && var.gcs_bucket_name != "" ? 1 : 0
  name   = var.gcs_bucket_name
  location = var.gcp_region

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.bucket_key[0].id
  }
}

# KMS Key for bucket encryption
resource "google_kms_key_ring" "bucket_key_ring" {
  count    = var.environment == "prod" && var.gcs_bucket_name != "" ? 1 : 0
  name     = "${var.project_name}-bucket-keyring-${local.name_suffix}"
  location = var.gcp_region
}

resource "google_kms_crypto_key" "bucket_key" {
  count           = var.environment == "prod" && var.gcs_bucket_name != "" ? 1 : 0
  name            = "${var.project_name}-bucket-key-${local.name_suffix}"
  key_ring        = google_kms_key_ring.bucket_key_ring[0].id
  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }
}

# Service Account for GKE nodes
resource "google_service_account" "gke_node" {
  count        = var.environment == "prod" && var.gcp_project_id != "" ? 1 : 0
  account_id   = "${var.project_name}-gke-node-${local.name_suffix}"
  display_name = "GKE Node Service Account"
  description  = "Service account for GKE nodes"
}

# IAM bindings for service account
resource "google_project_iam_member" "gke_node_logging" {
  count   = var.environment == "prod" && var.gcp_project_id != "" ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.gke_node[0].email}"
}

resource "google_project_iam_member" "gke_node_monitoring" {
  count   = var.environment == "prod" && var.gcp_project_id != "" ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.gke_node[0].email}"
}

resource "google_project_iam_member" "gke_node_monitoring_viewer" {
  count   = var.environment == "prod" && var.gcp_project_id != "" ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.gke_node[0].email}"
}

resource "google_project_iam_member" "gke_node_storage" {
  count   = var.environment == "prod" && var.gcs_bucket_name != "" ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.gke_node[0].email}"
}

# Service Account for Secret Manager access
resource "google_service_account" "secret_manager" {
  count        = var.environment == "prod" && var.enable_gcp_secret_manager ? 1 : 0
  account_id   = "${var.project_name}-secret-manager-${local.name_suffix}"
  display_name = "Secret Manager Service Account"
  description  = "Service account for accessing Secret Manager"
}

resource "google_project_iam_member" "secret_manager_accessor" {
  count   = var.environment == "prod" && var.enable_gcp_secret_manager ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.secret_manager[0].email}"
}

# Enable required APIs
resource "google_project_service" "container" {
  count   = var.environment == "prod" && var.gcp_project_id != "" ? 1 : 0
  project = var.gcp_project_id
  service = "container.googleapis.com"

  disable_dependent_services = true
}

resource "google_project_service" "compute" {
  count   = var.environment == "prod" && var.gcp_project_id != "" ? 1 : 0
  project = var.gcp_project_id
  service = "compute.googleapis.com"

  disable_dependent_services = true
}

resource "google_project_service" "storage" {
  count   = var.environment == "prod" && var.gcs_bucket_name != "" ? 1 : 0
  project = var.gcp_project_id
  service = "storage.googleapis.com"

  disable_dependent_services = true
}

resource "google_project_service" "secretmanager" {
  count   = var.environment == "prod" && var.enable_gcp_secret_manager ? 1 : 0
  project = var.gcp_project_id
  service = "secretmanager.googleapis.com"

  disable_dependent_services = true
}

resource "google_project_service" "kms" {
  count   = var.environment == "prod" && var.gcs_bucket_name != "" ? 1 : 0
  project = var.gcp_project_id
  service = "cloudkms.googleapis.com"

  disable_dependent_services = true
}

resource "google_project_service" "monitoring" {
  count   = var.environment == "prod" && var.enable_monitoring ? 1 : 0
  project = var.gcp_project_id
  service = "monitoring.googleapis.com"

  disable_dependent_services = true
}

resource "google_project_service" "logging" {
  count   = var.environment == "prod" && var.enable_logging ? 1 : 0
  project = var.gcp_project_id
  service = "logging.googleapis.com"

  disable_dependent_services = true
}

resource "google_project_service" "cloudsql" {
  count   = var.environment == "prod" ? 1 : 0
  project = var.gcp_project_id
  service = "sqladmin.googleapis.com"

  disable_dependent_services = true
}

resource "google_project_service" "redis" {
  count   = var.environment == "prod" ? 1 : 0
  project = var.gcp_project_id
  service = "redis.googleapis.com"

  disable_dependent_services = true
}

# Cloud SQL PostgreSQL Instance
resource "google_sql_database_instance" "postgres" {
  count   = var.environment == "prod" ? 1 : 0
  name    = "${var.project_name}-postgres-${local.name_suffix}"
  region  = var.gcp_region
  project = var.gcp_project_id

  database_version = "POSTGRES_${var.postgres_version}"

  settings {
    tier = "db-standard-2"
    
    disk_size = 100
    disk_type = "PD_SSD"
    disk_autoresize = true
    disk_autoresize_limit = 500

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      location                       = var.gcp_region
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.cancer_genomics[0].id
      require_ssl     = true
    }

    maintenance_window {
      day          = 7
      hour         = 3
      update_track = "stable"
    }

    database_flags {
      name  = "log_statement"
      value = "all"
    }

    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"
    }
  }

  deletion_protection = true

  depends_on = [
    google_project_service.cloudsql,
    google_compute_network.cancer_genomics
  ]
}

# Cloud SQL Database
resource "google_sql_database" "genomics_db" {
  count     = var.environment == "prod" ? 1 : 0
  name      = "cancer_genomics"
  instance  = google_sql_database_instance.postgres[0].name
  project   = var.gcp_project_id
  charset   = "UTF8"
  collation = "en_US.UTF8"
}

# Cloud SQL User
resource "google_sql_user" "genomics_user" {
  count    = var.environment == "prod" ? 1 : 0
  name     = "genomics_user"
  instance = google_sql_database_instance.postgres[0].name
  project  = var.gcp_project_id
  password = random_password.postgres_password[0].result
}

# Random password for PostgreSQL
resource "random_password" "postgres_password" {
  count   = var.environment == "prod" ? 1 : 0
  length  = 16
  special = true
}

# Memorystore Redis Instance
resource "google_redis_instance" "redis" {
  count          = var.environment == "prod" ? 1 : 0
  name           = "${var.project_name}-redis-${local.name_suffix}"
  tier           = "STANDARD_HA"
  memory_size_gb = 4
  region         = var.gcp_region
  project        = var.gcp_project_id

  location_id             = var.gcp_zone
  alternative_location_id = "${substr(var.gcp_region, 0, length(var.gcp_region) - 1)}b"

  authorized_network = google_compute_network.cancer_genomics[0].id

  redis_version     = "REDIS_${var.redis_version}_0"
  display_name      = "Cancer Genomics Redis"
  reserved_ip_range = "10.0.0.0/29"

  auth_enabled = true

  depends_on = [
    google_project_service.redis,
    google_compute_network.cancer_genomics
  ]
}

# Cloud Monitoring Workspace
resource "google_monitoring_workspace" "cancer_genomics" {
  count   = var.environment == "prod" && var.enable_monitoring ? 1 : 0
  project = var.gcp_project_id
  display_name = "Cancer Genomics Monitoring"
}

# Cloud Logging Sink
resource "google_logging_project_sink" "cancer_genomics_logs" {
  count   = var.environment == "prod" && var.enable_logging ? 1 : 0
  name    = "${var.project_name}-logs-sink-${local.name_suffix}"
  project = var.gcp_project_id

  destination = "storage.googleapis.com/${google_storage_bucket.logs[0].name}"

  filter = "resource.type=\"k8s_container\" AND resource.labels.namespace_name=\"cancer-genomics\""

  unique_writer_identity = true

  depends_on = [
    google_project_service.logging,
    google_storage_bucket.logs
  ]
}

# Storage bucket for logs
resource "google_storage_bucket" "logs" {
  count   = var.environment == "prod" && var.enable_logging ? 1 : 0
  name    = "${var.project_name}-logs-${local.name_suffix}"
  location = var.gcp_region
  project = var.gcp_project_id

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

# IAM binding for log sink
resource "google_project_iam_member" "log_sink_writer" {
  count   = var.environment == "prod" && var.enable_logging ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/storage.objectCreator"
  member  = google_logging_project_sink.cancer_genomics_logs[0].writer_identity
}

# Cloud Armor Security Policy
resource "google_compute_security_policy" "cancer_genomics" {
  count   = var.environment == "prod" ? 1 : 0
  name    = "${var.project_name}-security-policy-${local.name_suffix}"
  project = var.gcp_project_id

  # Default rule - allow all
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "default rule"
  }

  # Block known bad IPs
  rule {
    action   = "deny(403)"
    priority = "1000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["1.2.3.4/32"]  # Example bad IP
      }
    }
    description = "block bad IPs"
  }

  # Rate limiting rule
  rule {
    action   = "throttle"
    priority = "2000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
    }
    description = "rate limiting"
  }
}

# Cloud CDN Backend Bucket
resource "google_compute_backend_bucket" "static_assets" {
  count       = var.environment == "prod" ? 1 : 0
  name        = "${var.project_name}-static-assets-${local.name_suffix}"
  bucket_name = google_storage_bucket.static_assets[0].name
  project     = var.gcp_project_id
  enable_cdn  = true

  cdn_policy {
    cache_mode                   = "CACHE_ALL_STATIC"
    default_ttl                  = 3600
    client_ttl                   = 3600
    max_ttl                      = 86400
    negative_caching             = true
    serve_while_stale            = 86400
  }
}

# Storage bucket for static assets
resource "google_storage_bucket" "static_assets" {
  count   = var.environment == "prod" ? 1 : 0
  name    = "${var.project_name}-static-assets-${local.name_suffix}"
  location = var.gcp_region
  project = var.gcp_project_id

  uniform_bucket_level_access = true

  cors {
    origin          = ["https://${var.domain_name}", "https://${var.api_domain_name}"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }
}