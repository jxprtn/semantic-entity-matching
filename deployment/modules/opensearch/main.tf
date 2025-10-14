data "aws_iam_role" "example_managed_role" {
  name       = "AWSServiceRoleForAmazonOpenSearchService"
  depends_on = [null_resource.opensearch_service_linked_role]
}

# Ensure the OpenSearch service-linked role exists
resource "null_resource" "opensearch_service_linked_role" {
  # This will run on every apply, but the script checks if the role exists first
  triggers = {
    region = var.region
  }

  provisioner "local-exec" {
    command = <<-EOT
      # Check if the role exists
      if aws iam get-role --role-name AWSServiceRoleForAmazonOpenSearchService 2>/dev/null; then
        echo "Service-linked role AWSServiceRoleForAmazonOpenSearchService already exists"
      else
        echo "Creating service-linked role AWSServiceRoleForAmazonOpenSearchService..."
        aws iam create-service-linked-role --aws-service-name opensearchservice.amazonaws.com || {
          # If creation fails, check if it was created concurrently
          if aws iam get-role --role-name AWSServiceRoleForAmazonOpenSearchService 2>/dev/null; then
            echo "Role was created by another process"
          else
            echo "Failed to create service-linked role"
            exit 1
          fi
        }
      fi
    EOT
  }
}

locals {
  domain_arn = "arn:aws:es:${var.region}:${var.account_id}:domain/${var.domain_name}"
}

# IAM role for OpenSearch master user
resource "aws_iam_role" "opensearch_master_role" {
  name = "${var.domain_name}-master-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = var.current_user_arn
        }
        Action = "sts:AssumeRole"
      },
      {
        Effect = "Allow"
        Principal = {
          AWS = var.lambda_role_arn
        }
        Action = "sts:AssumeRole"
      },
      {
        Effect = "Allow"
        Principal = {
          Service = "es.${var.region}.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

# IAM policy for OpenSearch access
resource "aws_iam_role_policy" "opensearch_master_policy" {
  name = "${var.domain_name}-MasterPolicy"
  role = aws_iam_role.opensearch_master_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = aws_iam_role.opensearch_ml_connector_role.arn
      },
      {
        Effect   = "Allow"
        Action   = "es:ESHttp*"
        Resource = "${local.domain_arn}/*"
    }]
  })
}

# IAM role for OpenSearch ML connectors
resource "aws_iam_role" "opensearch_ml_connector_role" {
  name = "${var.domain_name}-RoleForMLConnector"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "es.${var.region}.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

# IAM policy for OpenSearch ML Connectors
resource "aws_iam_role_policy" "opensearch_ml_connector_policy" {
  name = "${var.domain_name}-MLConnectorPolicy"
  role = aws_iam_role.opensearch_ml_connector_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "es:ESHttp*"
        Resource = "${local.domain_arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = "bedrock:InvokeModel"
        Resource = "*"
    }]
  })
}


# OpenSearch cluster using terraform-aws-modules/opensearch/aws
module "opensearch" {
  source = "terraform-aws-modules/opensearch/aws"

  domain_name    = var.domain_name
  engine_version = var.engine_version

  # Cluster configuration - single node, no master
  cluster_config = {
    instance_type            = var.instance_type
    instance_count           = var.instance_count
    dedicated_master_enabled = false
    zone_awareness_enabled   = false
  }

  advanced_security_options = {
    enabled = false
  }

  # EBS storage configuration
  ebs_options = {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = 40
  }

  # Network configuration - public access for development
  domain_endpoint_options = {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  # Access policy - allow access from master role
  access_policy_statements = [
    {
      effect = "Allow"
      principals = [
        {
          type        = "AWS"
          identifiers = [aws_iam_role.opensearch_master_role.arn]
        }
      ]
      actions   = ["es:*"]
      resources = ["${local.domain_arn}/*"]
    }
  ]

  # Encryption at rest
  encrypt_at_rest = {
    enabled = true
  }

  # Node-to-node encryption
  node_to_node_encryption = {
    enabled = true
  }

  tags = merge(var.tags, {
    Purpose = "Vector search and document storage"
  })
}