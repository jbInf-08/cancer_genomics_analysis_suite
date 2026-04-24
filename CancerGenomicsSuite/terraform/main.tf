# Main Terraform configuration for Cancer Genomics Analysis Suite
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

# Configure providers
provider "aws" {
  region = var.aws_region
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "kubernetes" {
  config_path = var.kubeconfig_path
}

provider "helm" {
  kubernetes {
    config_path = var.kubeconfig_path
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "google_client_config" "default" {}

# Local values
locals {
  common_tags = {
    Project     = "cancer-genomics-analysis-suite"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
  
  # Generate random suffix for unique resource names
  name_suffix = random_string.suffix.result
}

# Random string for unique naming
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}
