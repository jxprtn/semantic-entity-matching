output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "lambda_function_arn" {
  description = "The ARN of the Lambda Function"
  value       = module.lambda_ingest.lambda_function_arn
}

output "lambda_function_name" {
  description = "The name of the Lambda Function"
  value       = module.lambda_ingest.lambda_function_name
}

output "lambda_function_invoke_arn" {
  description = "The Invoke ARN of the Lambda Function"
  value       = module.lambda_ingest.lambda_function_invoke_arn
}

output "lambda_role_arn" {
  description = "The ARN of the IAM role created for the Lambda Function"
  value       = module.lambda_ingest.lambda_role_arn
}

output "lambda_role_name" {
  description = "The name of the IAM role created for the Lambda Function"
  value       = module.lambda_ingest.lambda_role_name
}

# S3 Bucket outputs
output "s3_bucket_id" {
  description = "The name of the S3 bucket"
  value       = module.lambda_ingest.s3_bucket_id
}

output "s3_bucket_arn" {
  description = "The ARN of the S3 bucket"
  value       = module.lambda_ingest.s3_bucket_arn
}

output "s3_bucket_domain_name" {
  description = "The bucket domain name"
  value       = module.lambda_ingest.s3_bucket_domain_name
}

output "s3_bucket_regional_domain_name" {
  description = "The bucket region-specific domain name"
  value       = module.lambda_ingest.s3_bucket_regional_domain_name
}

# OpenSearch outputs
output "opensearch_domain_arn" {
  description = "The ARN of the OpenSearch domain"
  value       = module.opensearch-iam-only.domain_arn
}

output "opensearch_domain_id" {
  description = "The unique identifier for the OpenSearch domain"
  value       = module.opensearch-iam-only.domain_id
}

output "opensearch_domain_name" {
  description = "The name of the OpenSearch domain"
  value       = module.opensearch-iam-only.domain_name
}

output "opensearch_domain_endpoint" {
  description = "The domain-specific endpoint used to submit index, search, and data upload requests"
  value       = module.opensearch-iam-only.domain_endpoint
}

output "opensearch_master_role_arn" {
  description = "ARN of the OpenSearch master role for Cognito federated identity"
  value       = module.opensearch-iam-only.master_role_arn
}

output "opensearch_ml_connector_role_arn" {
  description = "ARN of the OpenSearch ML connector role"
  value       = module.opensearch-iam-only.ml_connector_role_arn
}
