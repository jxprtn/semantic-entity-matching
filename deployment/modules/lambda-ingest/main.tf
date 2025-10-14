# Data source to get current AWS region
data "aws_region" "current" {}

# S3 bucket for data ingestion using terraform-aws-modules/s3-bucket/aws
module "s3_bucket" {
  source = "terraform-aws-modules/s3-bucket/aws"

  bucket = var.bucket_name

  # Security settings
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  # Object ownership
  control_object_ownership = true
  object_ownership         = "BucketOwnerEnforced"

  # Versioning
  versioning = {
    enabled = var.enable_versioning
  }

  # Server-side encryption
  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm = "AES256"
      }
    }
  }

  # Lifecycle configuration for cost optimization
  lifecycle_rule = [
    {
      id     = "transition_to_ia"
      status = "Enabled"

      transition = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        },
        {
          days          = 90
          storage_class = "GLACIER"
        }
      ]
    }
  ]

  # Allow deletion of non-empty bucket for development
  force_destroy = var.force_destroy_bucket

  tags = merge(var.tags, {
    Purpose = "Data ingestion for OpenSearch"
  })
}

# Lambda function using terraform-aws-modules/lambda/aws
module "lambda_function" {
  source = "terraform-aws-modules/lambda/aws"

  function_name = var.function_name
  description   = var.description
  handler       = var.handler
  runtime       = var.runtime
  timeout       = var.timeout
  memory_size   = var.memory_size

  # Use AWS Lambda Layer for scientific Python libraries
  layers = var.layers

  # Source code configuration
  source_path = var.source_path

  # Environment variables
  environment_variables = var.environment_variables

  # IAM permissions
  attach_policy_statements = true
  policy_statements = {
    s3_read = {
      effect = "Allow"
      actions = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      resources = [
        module.s3_bucket.s3_bucket_arn,
        "${module.s3_bucket.s3_bucket_arn}/*"
      ]
    }
    opensearch_access = {
      effect = "Allow"
      actions = [
        "es:ESHttpDelete",
        "es:ESHttpGet",
        "es:ESHttpHead",
        "es:ESHttpPost",
        "es:ESHttpPut"
      ]
      resources = ["*"]
    }
    bedrock_access = {
      effect = "Allow"
      actions = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ]
      resources = ["*"]
    }
  }

  tags = var.tags
}

