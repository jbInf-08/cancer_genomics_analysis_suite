# AWS Infrastructure for Cancer Genomics Analysis Suite

# EKS Cluster
resource "aws_eks_cluster" "cancer_genomics" {
  count    = var.environment == "prod" ? 1 : 0
  name     = "${var.project_name}-${var.environment}-${local.name_suffix}"
  role_arn = aws_iam_role.eks_cluster[0].arn
  version  = "1.28"

  vpc_config {
    subnet_ids              = aws_subnet.private[*].id
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = ["0.0.0.0/0"]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller,
  ]

  tags = local.common_tags
}

# EKS Node Group
resource "aws_eks_node_group" "cancer_genomics" {
  count           = var.environment == "prod" ? 1 : 0
  cluster_name    = aws_eks_cluster.cancer_genomics[0].name
  node_group_name = "${var.project_name}-nodes-${local.name_suffix}"
  node_role_arn   = aws_iam_role.eks_node_group[0].arn
  subnet_ids      = aws_subnet.private[*].id

  scaling_config {
    desired_size = var.aws_node_count
    max_size     = var.aws_node_count * 2
    min_size     = 1
  }

  update_config {
    max_unavailable = 1
  }

  instance_types = [var.aws_instance_type]

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_read_only,
  ]

  tags = local.common_tags
}

# VPC
resource "aws_vpc" "cancer_genomics" {
  count            = var.environment == "prod" ? 1 : 0
  cidr_block       = "10.0.0.0/16"
  instance_tenancy = "default"

  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-vpc-${local.name_suffix}"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "cancer_genomics" {
  count  = var.environment == "prod" ? 1 : 0
  vpc_id = aws_vpc.cancer_genomics[0].id

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-igw-${local.name_suffix}"
  })
}

# Public Subnets
resource "aws_subnet" "public" {
  count             = var.environment == "prod" ? length(var.aws_availability_zones) : 0
  vpc_id            = aws_vpc.cancer_genomics[0].id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = var.aws_availability_zones[count.index]

  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-public-subnet-${count.index + 1}-${local.name_suffix}"
    Type = "public"
  })
}

# Private Subnets
resource "aws_subnet" "private" {
  count             = var.environment == "prod" ? length(var.aws_availability_zones) : 0
  vpc_id            = aws_vpc.cancer_genomics[0].id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = var.aws_availability_zones[count.index]

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-private-subnet-${count.index + 1}-${local.name_suffix}"
    Type = "private"
  })
}

# NAT Gateway
resource "aws_eip" "nat" {
  count  = var.environment == "prod" ? length(var.aws_availability_zones) : 0
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-nat-eip-${count.index + 1}-${local.name_suffix}"
  })
}

resource "aws_nat_gateway" "cancer_genomics" {
  count         = var.environment == "prod" ? length(var.aws_availability_zones) : 0
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-nat-gateway-${count.index + 1}-${local.name_suffix}"
  })

  depends_on = [aws_internet_gateway.cancer_genomics]
}

# Route Tables
resource "aws_route_table" "public" {
  count  = var.environment == "prod" ? 1 : 0
  vpc_id = aws_vpc.cancer_genomics[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.cancer_genomics[0].id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-public-rt-${local.name_suffix}"
  })
}

resource "aws_route_table" "private" {
  count  = var.environment == "prod" ? length(var.aws_availability_zones) : 0
  vpc_id = aws_vpc.cancer_genomics[0].id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.cancer_genomics[count.index].id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-private-rt-${count.index + 1}-${local.name_suffix}"
  })
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = var.environment == "prod" ? length(var.aws_availability_zones) : 0
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_route_table_association" "private" {
  count          = var.environment == "prod" ? length(var.aws_availability_zones) : 0
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# S3 Bucket for Artifacts
resource "aws_s3_bucket" "artifacts" {
  count  = var.environment == "prod" && var.s3_bucket_name != "" ? 1 : 0
  bucket = var.s3_bucket_name

  tags = local.common_tags
}

resource "aws_s3_bucket_versioning" "artifacts" {
  count  = var.environment == "prod" && var.s3_bucket_name != "" ? 1 : 0
  bucket = aws_s3_bucket.artifacts[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "artifacts" {
  count  = var.environment == "prod" && var.s3_bucket_name != "" ? 1 : 0
  bucket = aws_s3_bucket.artifacts[0].id

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  count  = var.environment == "prod" && var.s3_bucket_name != "" ? 1 : 0
  bucket = aws_s3_bucket.artifacts[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM Roles and Policies
resource "aws_iam_role" "eks_cluster" {
  count = var.environment == "prod" ? 1 : 0
  name  = "${var.project_name}-eks-cluster-role-${local.name_suffix}"

  assume_role_policy = jsonencode({
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
    Version = "2012-10-17"
  })

  tags = local.common_tags
}

resource "aws_iam_role" "eks_node_group" {
  count = var.environment == "prod" ? 1 : 0
  name  = "${var.project_name}-eks-node-group-role-${local.name_suffix}"

  assume_role_policy = jsonencode({
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
    Version = "2012-10-17"
  })

  tags = local.common_tags
}

# IAM Policy Attachments
resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  count      = var.environment == "prod" ? 1 : 0
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster[0].name
}

resource "aws_iam_role_policy_attachment" "eks_vpc_resource_controller" {
  count      = var.environment == "prod" ? 1 : 0
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = aws_iam_role.eks_cluster[0].name
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  count      = var.environment == "prod" ? 1 : 0
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node_group[0].name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  count      = var.environment == "prod" ? 1 : 0
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node_group[0].name
}

resource "aws_iam_role_policy_attachment" "eks_container_registry_read_only" {
  count      = var.environment == "prod" ? 1 : 0
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node_group[0].name
}

# AWS Secrets Manager Integration
resource "aws_iam_policy" "secrets_manager_access" {
  count = var.environment == "prod" && var.enable_aws_secrets_manager ? 1 : 0
  name  = "${var.project_name}-secrets-manager-access-${local.name_suffix}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:*:secret:${var.project_name}/*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "secrets_manager_access" {
  count      = var.environment == "prod" && var.enable_aws_secrets_manager ? 1 : 0
  policy_arn = aws_iam_policy.secrets_manager_access[0].arn
  role       = aws_iam_role.eks_node_group[0].name
}

# RDS PostgreSQL Instance
resource "aws_db_subnet_group" "cancer_genomics" {
  count      = var.environment == "prod" ? 1 : 0
  name       = "${var.project_name}-db-subnet-group-${local.name_suffix}"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-db-subnet-group-${local.name_suffix}"
  })
}

resource "aws_security_group" "rds" {
  count       = var.environment == "prod" ? 1 : 0
  name        = "${var.project_name}-rds-sg-${local.name_suffix}"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = aws_vpc.cancer_genomics[0].id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_eks_cluster.cancer_genomics[0].vpc_config[0].cluster_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-rds-sg-${local.name_suffix}"
  })
}

resource "aws_db_parameter_group" "cancer_genomics" {
  count  = var.environment == "prod" ? 1 : 0
  family = "postgres15"
  name   = "${var.project_name}-db-params-${local.name_suffix}"

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  tags = local.common_tags
}

resource "aws_db_instance" "postgres" {
  count             = var.environment == "prod" ? 1 : 0
  identifier        = "${var.project_name}-postgres-${local.name_suffix}"
  engine            = "postgres"
  engine_version    = var.postgres_version
  instance_class    = "db.t3.medium"
  allocated_storage = 100
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "cancer_genomics"
  username = "genomics_user"
  password = random_password.postgres_password[0].result

  vpc_security_group_ids = [aws_security_group.rds[0].id]
  db_subnet_group_name   = aws_db_subnet_group.cancer_genomics[0].name
  parameter_group_name   = aws_db_parameter_group.cancer_genomics[0].name

  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  skip_final_snapshot = false
  final_snapshot_identifier = "${var.project_name}-postgres-final-snapshot-${local.name_suffix}"

  deletion_protection = true

  performance_insights_enabled = true
  monitoring_interval         = 60
  monitoring_role_arn        = aws_iam_role.rds_enhanced_monitoring[0].arn

  tags = local.common_tags
}

# Random password for PostgreSQL
resource "random_password" "postgres_password" {
  count   = var.environment == "prod" ? 1 : 0
  length  = 16
  special = true
}

# IAM role for RDS Enhanced Monitoring
resource "aws_iam_role" "rds_enhanced_monitoring" {
  count = var.environment == "prod" ? 1 : 0
  name  = "${var.project_name}-rds-enhanced-monitoring-${local.name_suffix}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  count      = var.environment == "prod" ? 1 : 0
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
  role       = aws_iam_role.rds_enhanced_monitoring[0].name
}

# ElastiCache Redis Cluster
resource "aws_elasticache_subnet_group" "cancer_genomics" {
  count      = var.environment == "prod" ? 1 : 0
  name       = "${var.project_name}-cache-subnet-group-${local.name_suffix}"
  subnet_ids = aws_subnet.private[*].id

  tags = local.common_tags
}

resource "aws_security_group" "elasticache" {
  count       = var.environment == "prod" ? 1 : 0
  name        = "${var.project_name}-elasticache-sg-${local.name_suffix}"
  description = "Security group for ElastiCache Redis"
  vpc_id      = aws_vpc.cancer_genomics[0].id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_eks_cluster.cancer_genomics[0].vpc_config[0].cluster_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-elasticache-sg-${local.name_suffix}"
  })
}

resource "aws_elasticache_replication_group" "redis" {
  count               = var.environment == "prod" ? 1 : 0
  replication_group_id = "${var.project_name}-redis-${local.name_suffix}"
  description         = "Redis cluster for Cancer Genomics Analysis Suite"

  node_type            = "cache.t3.micro"
  port                 = 6379
  parameter_group_name = "default.redis7"

  num_cache_clusters = 2
  automatic_failover_enabled = true
  multi_az_enabled   = true

  subnet_group_name  = aws_elasticache_subnet_group.cancer_genomics[0].name
  security_group_ids = [aws_security_group.elasticache[0].id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis_auth_token[0].result

  snapshot_retention_limit = 5
  snapshot_window         = "03:00-05:00"
  maintenance_window      = "sun:05:00-sun:07:00"

  tags = local.common_tags
}

# Random auth token for Redis
resource "random_password" "redis_auth_token" {
  count   = var.environment == "prod" ? 1 : 0
  length  = 32
  special = true
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "cancer_genomics" {
  count             = var.environment == "prod" ? 1 : 0
  name              = "/aws/eks/${var.project_name}-${var.environment}-${local.name_suffix}/cluster"
  retention_in_days = 30

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "application_logs" {
  count             = var.environment == "prod" ? 1 : 0
  name              = "/aws/eks/${var.project_name}-${var.environment}-${local.name_suffix}/application"
  retention_in_days = 30

  tags = local.common_tags
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  count               = var.environment == "prod" ? 1 : 0
  alarm_name          = "${var.project_name}-high-cpu-${local.name_suffix}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EKS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors EKS cluster CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    ClusterName = aws_eks_cluster.cancer_genomics[0].name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "high_memory" {
  count               = var.environment == "prod" ? 1 : 0
  alarm_name          = "${var.project_name}-high-memory-${local.name_suffix}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/EKS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors EKS cluster memory utilization"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    ClusterName = aws_eks_cluster.cancer_genomics[0].name
  }

  tags = local.common_tags
}

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  count = var.environment == "prod" ? 1 : 0
  name  = "${var.project_name}-alerts-${local.name_suffix}"

  tags = local.common_tags
}

# Application Load Balancer
resource "aws_lb" "cancer_genomics" {
  count              = var.environment == "prod" ? 1 : 0
  name               = "${var.project_name}-alb-${local.name_suffix}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb[0].id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = true

  tags = local.common_tags
}

resource "aws_security_group" "alb" {
  count       = var.environment == "prod" ? 1 : 0
  name        = "${var.project_name}-alb-sg-${local.name_suffix}"
  description = "Security group for Application Load Balancer"
  vpc_id      = aws_vpc.cancer_genomics[0].id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-alb-sg-${local.name_suffix}"
  })
}

# ALB Target Group
resource "aws_lb_target_group" "cancer_genomics" {
  count    = var.environment == "prod" ? 1 : 0
  name     = "${var.project_name}-tg-${local.name_suffix}"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.cancer_genomics[0].id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    port                = "traffic-port"
    protocol            = "HTTP"
  }

  tags = local.common_tags
}

# ALB Listener
resource "aws_lb_listener" "cancer_genomics" {
  count             = var.environment == "prod" ? 1 : 0
  load_balancer_arn = aws_lb.cancer_genomics[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.cancer_genomics[0].arn
  }
}

# WAF Web ACL
resource "aws_wafv2_web_acl" "cancer_genomics" {
  count    = var.environment == "prod" ? 1 : 0
  name     = "${var.project_name}-waf-${local.name_suffix}"
  scope    = "REGIONAL"
  provider = aws

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "KnownBadInputsRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "CancerGenomicsWebACL"
    sampled_requests_enabled   = true
  }

  tags = local.common_tags
}

# WAF Association with ALB
resource "aws_wafv2_web_acl_association" "cancer_genomics" {
  count        = var.environment == "prod" ? 1 : 0
  resource_arn = aws_lb.cancer_genomics[0].arn
  web_acl_arn  = aws_wafv2_web_acl.cancer_genomics[0].arn
}

# Route 53 Hosted Zone
resource "aws_route53_zone" "cancer_genomics" {
  count = var.environment == "prod" ? 1 : 0
  name  = var.domain_name

  tags = local.common_tags
}

# Route 53 Record for ALB
resource "aws_route53_record" "cancer_genomics" {
  count   = var.environment == "prod" ? 1 : 0
  zone_id = aws_route53_zone.cancer_genomics[0].zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.cancer_genomics[0].dns_name
    zone_id                = aws_lb.cancer_genomics[0].zone_id
    evaluate_target_health = true
  }
}

# Route 53 Record for API
resource "aws_route53_record" "api" {
  count   = var.environment == "prod" ? 1 : 0
  zone_id = aws_route53_zone.cancer_genomics[0].zone_id
  name    = var.api_domain_name
  type    = "A"

  alias {
    name                   = aws_lb.cancer_genomics[0].dns_name
    zone_id                = aws_lb.cancer_genomics[0].zone_id
    evaluate_target_health = true
  }
}