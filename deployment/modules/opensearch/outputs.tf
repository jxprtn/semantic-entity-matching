# OpenSearch domain outputs
output "domain_arn" {
  description = "ARN of the OpenSearch domain"
  value       = module.opensearch.domain_arn
}

output "domain_endpoint" {
  description = "Domain-specific endpoint used to submit index, search, and data upload requests"
  value       = module.opensearch.domain_endpoint
}

output "domain_id" {
  description = "Unique identifier for the domain"
  value       = module.opensearch.domain_id
}

output "domain_name" {
  description = "Name of the OpenSearch domain"
  value       = module.opensearch.domain_name
}

# IAM roles
output "master_role_arn" {
  description = "ARN of the OpenSearch master role"
  value       = aws_iam_role.opensearch_master_role.arn
}

output "ml_connector_role_arn" {
  description = "ARN of the OpenSearch ML connector role"
  value       = aws_iam_role.opensearch_ml_connector_role.arn
}
