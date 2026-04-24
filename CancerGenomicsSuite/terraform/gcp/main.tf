# GCP Provider Configuration
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
  
  backend "gcs" {
    bucket = "cancer-genomics-terraform-state"
    prefix = "gcp/terraform.tfstate"
  }
}

# Google Provider
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}

provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}

# Data sources
data "google_client_config" "current" {}

data "google_compute_zones" "available" {
  region = var.gcp_region
}

# Local values
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  
  common_labels = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  }
  
  # Network CIDR blocks
  vpc_cidr = "10.0.0.0/16"
  
  # Subnet CIDR blocks
  public_subnet_cidr  = "10.0.1.0/24"
  private_subnet_cidr = "10.0.2.0/24"
  
  # Availability zones
  zones = slice(data.google_compute_zones.available.names, 0, 3)
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
    "cloudsql.googleapis.com",
    "redis.googleapis.com",
    "storage.googleapis.com",
    "secretmanager.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "dns.googleapis.com",
    "certificatemanager.googleapis.com",
    "networksecurity.googleapis.com",
    "networkconnectivity.googleapis.com"
  ])
  
  service = each.value
  
  disable_on_destroy = false
}

# VPC Network
resource "google_compute_network" "main" {
  name                    = "${local.name_prefix}-vpc"
  auto_create_subnetworks = false
  mtu                     = 1460
  
  depends_on = [google_project_service.required_apis]
}

# Public Subnet
resource "google_compute_subnetwork" "public" {
  name          = "${local.name_prefix}-public-subnet"
  ip_cidr_range = local.public_subnet_cidr
  region        = var.gcp_region
  network       = google_compute_network.main.id
  
  private_ip_google_access = true
}

# Private Subnet
resource "google_compute_subnetwork" "private" {
  name          = "${local.name_prefix}-private-subnet"
  ip_cidr_range = local.private_subnet_cidr
  region        = var.gcp_region
  network       = google_compute_network.main.id
  
  private_ip_google_access = true
}

# Cloud NAT for private subnet
resource "google_compute_router" "main" {
  name    = "${local.name_prefix}-router"
  region  = var.gcp_region
  network = google_compute_network.main.id
}

resource "google_compute_router_nat" "main" {
  name                               = "${local.name_prefix}-nat"
  router                            = google_compute_router.main.name
  region                            = var.gcp_region
  nat_ip_allocate_option            = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Firewall Rules
resource "google_compute_firewall" "allow_http" {
  name    = "${local.name_prefix}-allow-http"
  network = google_compute_network.main.name
  
  allow {
    protocol = "tcp"
    ports    = ["80"]
  }
  
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["http-server"]
}

resource "google_compute_firewall" "allow_https" {
  name    = "${local.name_prefix}-allow-https"
  network = google_compute_network.main.name
  
  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
  
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["https-server"]
}

resource "google_compute_firewall" "allow_internal" {
  name    = "${local.name_prefix}-allow-internal"
  network = google_compute_network.main.name
  
  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "icmp"
  }
  
  source_ranges = [local.vpc_cidr]
}

# GKE Cluster
resource "google_container_cluster" "main" {
  name     = "${local.name_prefix}-gke"
  location = var.gcp_region
  
  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1
  
  network    = google_compute_network.main.name
  subnetwork = google_compute_subnetwork.private.name
  
  # Enable network policy
  network_policy {
    enabled = true
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
  
  # Enable workload identity
  workload_identity_config {
    workload_pool = "${var.gcp_project_id}.svc.id.goog"
  }
  
  # Enable IP aliasing
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }
  
  # Enable binary authorization
  binary_authorization {
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }
  
  # Enable network policy
  addons_config {
    network_policy_config {
      disabled = false
    }
    
    horizontal_pod_autoscaling {
      disabled = false
    }
    
    http_load_balancing {
      disabled = false
    }
  }
  
  # Enable maintenance window
  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"
    }
  }
  
  # Enable monitoring
  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS", "APISERVER", "CONTROLLER_MANAGER", "SCHEDULER"]
  }
  
  # Enable logging
  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }
  
  depends_on = [google_project_service.required_apis]
}

# Node Pools
resource "google_container_node_pool" "general" {
  name       = "general"
  location   = var.gcp_region
  cluster    = google_container_cluster.main.name
  node_count = 3
  
  node_config {
    preemptible  = false
    machine_type = "e2-medium"
    disk_size_gb = 50
    disk_type    = "pd-standard"
    
    # Enable workload identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    
    # Enable secure boot
    shielded_instance_config {
      enable_secure_boot = true
    }
    
    # Enable integrity monitoring
    shielded_instance_config {
      enable_integrity_monitoring = true
    }
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    labels = {
      role = "general"
    }
    
    tags = ["gke-node", "general"]
  }
  
  autoscaling {
    min_node_count = 2
    max_node_count = 10
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

resource "google_container_node_pool" "compute" {
  name       = "compute"
  location   = var.gcp_region
  cluster    = google_container_cluster.main.name
  node_count = 2
  
  node_config {
    preemptible  = true
    machine_type = "c2-standard-4"
    disk_size_gb = 100
    disk_type    = "pd-ssd"
    
    # Enable workload identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    
    # Enable secure boot
    shielded_instance_config {
      enable_secure_boot = true
    }
    
    # Enable integrity monitoring
    shielded_instance_config {
      enable_integrity_monitoring = true
    }
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    labels = {
      role = "compute"
    }
    
    taint {
      key    = "compute"
      value  = "true"
      effect = "NO_SCHEDULE"
    }
    
    tags = ["gke-node", "compute"]
  }
  
  autoscaling {
    min_node_count = 0
    max_node_count = 20
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

resource "google_container_node_pool" "storage" {
  name       = "storage"
  location   = var.gcp_region
  cluster    = google_container_cluster.main.name
  node_count = 2
  
  node_config {
    preemptible  = false
    machine_type = "n2-standard-4"
    disk_size_gb = 200
    disk_type    = "pd-ssd"
    
    # Enable workload identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    
    # Enable secure boot
    shielded_instance_config {
      enable_secure_boot = true
    }
    
    # Enable integrity monitoring
    shielded_instance_config {
      enable_integrity_monitoring = true
    }
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    labels = {
      role = "storage"
    }
    
    taint {
      key    = "storage"
      value  = "true"
      effect = "NO_SCHEDULE"
    }
    
    tags = ["gke-node", "storage"]
  }
  
  autoscaling {
    min_node_count = 1
    max_node_count = 5
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# Cloud SQL PostgreSQL
resource "google_sql_database_instance" "postgres" {
  name             = "${local.name_prefix}-postgres"
  database_version = "POSTGRES_15"
  region           = var.gcp_region
  
  settings {
    tier                        = var.cloud_sql_tier
    availability_type           = var.enable_multi_az ? "REGIONAL" : "ZONAL"
    disk_type                   = "PD_SSD"
    disk_size                   = var.cloud_sql_disk_size
    disk_autoresize             = true
    disk_autoresize_limit       = 1000
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      location                       = var.gcp_region
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
      require_ssl     = true
    }
    
    database_flags {
      name  = "log_statement"
      value = "all"
    }
    
    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"
    }
    
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
    
    maintenance_window {
      day          = 7
      hour         = 3
      update_track = "stable"
    }
  }
  
  deletion_protection = var.environment == "production"
  
  depends_on = [google_project_service.required_apis]
}

resource "google_sql_database" "genomics" {
  name     = "genomics_db"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "postgres" {
  name     = "postgres"
  instance = google_sql_database_instance.postgres.name
  password = random_password.postgres_password.result
}

# Memorystore Redis
resource "google_redis_instance" "redis" {
  name           = "${local.name_prefix}-redis"
  tier           = var.redis_tier
  memory_size_gb = var.redis_memory_size_gb
  region         = var.gcp_region
  
  authorized_network = google_compute_network.main.id
  
  redis_version     = "REDIS_7_0"
  display_name      = "Cancer Genomics Redis"
  
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
        seconds = 0
        nanos   = 0
      }
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

# Cloud Storage Buckets
resource "google_storage_bucket" "data" {
  name          = "${local.name_prefix}-data-${random_string.bucket_suffix.result}"
  location      = var.gcp_region
  storage_class = "STANDARD"
  
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
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
  
  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }
  
  encryption {
    default_kms_key_name = google_kms_crypto_key.bucket_encryption.id
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_storage_bucket" "artifacts" {
  name          = "${local.name_prefix}-artifacts-${random_string.bucket_suffix.result}"
  location      = var.gcp_region
  storage_class = "STANDARD"
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
  
  encryption {
    default_kms_key_name = google_kms_crypto_key.bucket_encryption.id
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_storage_bucket" "backups" {
  name          = "${local.name_prefix}-backups-${random_string.bucket_suffix.result}"
  location      = var.gcp_region
  storage_class = "STANDARD"
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }
  
  encryption {
    default_kms_key_name = google_kms_crypto_key.bucket_encryption.id
  }
  
  depends_on = [google_project_service.required_apis]
}

# KMS for encryption
resource "google_kms_key_ring" "bucket_encryption" {
  name     = "${local.name_prefix}-bucket-encryption"
  location = var.gcp_region
}

resource "google_kms_crypto_key" "bucket_encryption" {
  name            = "bucket-encryption-key"
  key_ring        = google_kms_key_ring.bucket_encryption.id
  rotation_period = "7776000s"  # 90 days
  
  lifecycle {
    prevent_destroy = true
  }
}

# Secret Manager
resource "google_secret_manager_secret" "database" {
  secret_id = "${local.name_prefix}-database-password"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "database" {
  secret = google_secret_manager_secret.database.id
  secret_data = jsonencode({
    POSTGRES_PASSWORD = random_password.postgres_password.result
    POSTGRES_USER     = "postgres"
    POSTGRES_DB       = "genomics_db"
  })
}

resource "google_secret_manager_secret" "redis" {
  secret_id = "${local.name_prefix}-redis-password"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "redis" {
  secret = google_secret_manager_secret.redis.id
  secret_data = jsonencode({
    REDIS_PASSWORD = random_password.redis_password.result
  })
}

resource "google_secret_manager_secret" "app" {
  secret_id = "${local.name_prefix}-app-secret-key"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "app" {
  secret = google_secret_manager_secret.app.id
  secret_data = jsonencode({
    SECRET_KEY     = random_password.app_secret_key.result
    JWT_SECRET_KEY = random_password.jwt_secret_key.result
  })
}

# Service Account for GKE
resource "google_service_account" "gke_service_account" {
  account_id   = "${local.name_prefix}-gke-sa"
  display_name = "GKE Service Account for Cancer Genomics"
  
  depends_on = [google_project_service.required_apis]
}

# IAM bindings for service account
resource "google_project_iam_member" "gke_service_account" {
  for_each = toset([
    "roles/storage.objectViewer",
    "roles/storage.objectAdmin",
    "roles/secretmanager.secretAccessor",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
    "roles/cloudsql.client"
  ])
  
  project = var.gcp_project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.gke_service_account.email}"
}

# Workload Identity binding
resource "google_service_account_iam_member" "gke_workload_identity" {
  service_account_id = google_service_account.gke_service_account.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.gcp_project_id}.svc.id.goog[${var.kubernetes_namespace}/cancer-genomics-analysis-suite]"
}

# Random passwords
resource "random_password" "postgres_password" {
  length  = 32
  special = true
}

resource "random_password" "redis_password" {
  length  = 32
  special = true
}

resource "random_password" "app_secret_key" {
  length  = 64
  special = true
}

resource "random_password" "jwt_secret_key" {
  length  = 64
  special = true
}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Cloud DNS (if domain is provided)
resource "google_dns_managed_zone" "main" {
  count       = var.domain_name != "" ? 1 : 0
  name        = "${local.name_prefix}-dns-zone"
  dns_name    = "${var.domain_name}."
  description = "DNS zone for cancer genomics analysis suite"
  
  depends_on = [google_project_service.required_apis]
}

# Cloud Load Balancer
resource "google_compute_global_address" "main" {
  name = "${local.name_prefix}-global-ip"
}

resource "google_compute_global_forwarding_rule" "main" {
  name       = "${local.name_prefix}-forwarding-rule"
  target     = google_compute_target_https_proxy.main.id
  port_range = "443"
  ip_address = google_compute_global_address.main.address
}

resource "google_compute_target_https_proxy" "main" {
  name             = "${local.name_prefix}-https-proxy"
  url_map          = google_compute_url_map.main.id
  ssl_certificates = var.domain_name != "" ? [google_compute_managed_ssl_certificate.main[0].id] : []
}

resource "google_compute_url_map" "main" {
  name            = "${local.name_prefix}-url-map"
  default_service = google_compute_backend_service.main.id
}

resource "google_compute_backend_service" "main" {
  name        = "${local.name_prefix}-backend-service"
  protocol    = "HTTP"
  port_name   = "http"
  timeout_sec = 30
  
  backend {
    group = google_container_node_pool.general.instance_group_urls[0]
  }
  
  health_checks = [google_compute_health_check.main.id]
}

resource "google_compute_health_check" "main" {
  name               = "${local.name_prefix}-health-check"
  check_interval_sec = 5
  timeout_sec        = 5
  healthy_threshold  = 2
  unhealthy_threshold = 3
  
  http_health_check {
    request_path = "/health"
    port         = "80"
  }
}

# SSL Certificate (if domain is provided)
resource "google_compute_managed_ssl_certificate" "main" {
  count   = var.domain_name != "" ? 1 : 0
  name    = "${local.name_prefix}-ssl-cert"
  
  managed {
    domains = [var.domain_name, "*.${var.domain_name}"]
  }
}

# DNS Record (if domain is provided)
resource "google_dns_record_set" "main" {
  count        = var.domain_name != "" ? 1 : 0
  name         = "${var.domain_name}."
  type         = "A"
  ttl          = 300
  managed_zone = google_dns_managed_zone.main[0].name
  
  rrdatas = [google_compute_global_address.main.address]
}

# Cloud Logging
resource "google_logging_project_sink" "main" {
  name        = "${local.name_prefix}-log-sink"
  destination = "storage.googleapis.com/${google_storage_bucket.backups.name}/logs"
  
  filter = "resource.type=\"gke_cluster\" OR resource.type=\"gke_node_pool\" OR resource.type=\"cloudsql_database\""
  
  unique_writer_identity = true
}

# Cloud Monitoring
resource "google_monitoring_notification_channel" "email" {
  count        = var.alert_email != "" ? 1 : 0
  display_name = "Email Notification Channel"
  type         = "email"
  
  labels = {
    email_address = var.alert_email
  }
}

resource "google_monitoring_alert_policy" "high_cpu" {
  display_name = "High CPU Usage"
  combiner     = "OR"
  
  conditions {
    display_name = "High CPU Usage"
    
    condition_threshold {
      filter          = "resource.type=\"gke_container\" AND metric.type=\"kubernetes.io/container/cpu/core_usage_time\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.8
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = var.alert_email != "" ? [google_monitoring_notification_channel.email[0].id] : []
  
  depends_on = [google_project_service.required_apis]
}

resource "google_monitoring_alert_policy" "high_memory" {
  display_name = "High Memory Usage"
  combiner     = "OR"
  
  conditions {
    display_name = "High Memory Usage"
    
    condition_threshold {
      filter          = "resource.type=\"gke_container\" AND metric.type=\"kubernetes.io/container/memory/used_bytes\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.9
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = var.alert_email != "" ? [google_monitoring_notification_channel.email[0].id] : []
  
  depends_on = [google_project_service.required_apis]
}

# Cloud Backup
resource "google_storage_transfer_job" "backup" {
  description = "Backup job for cancer genomics data"
  
  transfer_spec {
    gcs_data_source {
      bucket_name = google_storage_bucket.data.name
    }
    
    gcs_data_sink {
      bucket_name = google_storage_bucket.backups.name
    }
  }
  
  schedule {
    schedule_start_date {
      year  = 2024
      month = 1
      day   = 1
    }
    schedule_end_date {
      year  = 2025
      month = 12
      day   = 31
    }
    start_time_of_day {
      hours   = 2
      minutes = 0
      seconds = 0
      nanos   = 0
    }
    repeat_interval = "86400s"  # Daily
  }
  
  depends_on = [google_project_service.required_apis]
}
