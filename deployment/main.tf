terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.1"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data source to get current AWS account ID and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}



# Lambda function and S3 bucket using local module
module "lambda_ingest" {
  source = "./modules/lambda-ingest"

  function_name = var.function_name
  description   = "Lambda function for ingesting data from S3 files into OpenSearch"
  handler       = "main.lambda_handler"
  runtime       = "python3.12"
  timeout       = 300
  memory_size   = 1024

  # Use AWS Lambda Layer for scientific Python libraries
  layers = [
    "arn:aws:lambda:${data.aws_region.current.region}:336392948345:layer:AWSSDKPandas-Python312:19"
  ]

  # Source code configuration - pandas comes from AWS layer
  source_path = [
    {
      path             = "../apps/lambda/ingest"
      pip_requirements = true
    },
    {
      path          = "../lib"
      prefix_in_zip = "lib"
    }
  ]

  # Environment variables
  environment_variables = {
    PYTHONPATH = "/var/task:/var/task/lib:/opt/python"
  }

  # S3 bucket configuration
  bucket_name          = var.bucket_name
  enable_versioning    = var.enable_versioning
  force_destroy_bucket = var.force_destroy_bucket

  tags = var.tags
}

# OpenSearch module
module "opensearch-iam-only" {
  source = "./modules/opensearch"

  domain_name      = var.opensearch_domain_name
  region           = data.aws_region.current.id
  account_id       = data.aws_caller_identity.current.account_id
  current_user_arn = data.aws_caller_identity.current.arn
  lambda_role_arn  = module.lambda_ingest.lambda_role_arn
  instance_count   = var.opensearch_instance_count
  instance_type    = var.opensearch_instance_type
  engine_version   = var.opensearch_version

  tags = var.tags
}

