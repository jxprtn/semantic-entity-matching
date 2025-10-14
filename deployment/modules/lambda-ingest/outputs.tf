output "lambda_function_arn" {
  description = "The ARN of the Lambda function"
  value       = module.lambda_function.lambda_function_arn
}

output "lambda_function_name" {
  description = "The name of the Lambda function"
  value       = module.lambda_function.lambda_function_name
}

output "lambda_function_invoke_arn" {
  description = "The invoke ARN of the Lambda function"
  value       = module.lambda_function.lambda_function_invoke_arn
}

output "lambda_function_qualified_arn" {
  description = "The qualified ARN of the Lambda function"
  value       = module.lambda_function.lambda_function_qualified_arn
}

output "lambda_function_version" {
  description = "Latest published version of the Lambda function"
  value       = module.lambda_function.lambda_function_version
}

output "lambda_role_arn" {
  description = "The ARN of the IAM role created for the Lambda function"
  value       = module.lambda_function.lambda_role_arn
}

output "lambda_role_name" {
  description = "The name of the IAM role created for the Lambda function"
  value       = module.lambda_function.lambda_role_name
}

# S3 Bucket outputs
output "s3_bucket_id" {
  description = "The name of the S3 bucket"
  value       = module.s3_bucket.s3_bucket_id
}

output "s3_bucket_arn" {
  description = "The ARN of the S3 bucket"
  value       = module.s3_bucket.s3_bucket_arn
}

output "s3_bucket_domain_name" {
  description = "The bucket domain name"
  value       = module.s3_bucket.s3_bucket_bucket_domain_name
}

output "s3_bucket_regional_domain_name" {
  description = "The bucket region-specific domain name"
  value       = module.s3_bucket.s3_bucket_bucket_regional_domain_name
}