variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-1"
}

variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "opensearch-ingest-lambda"
}

variable "bucket_name" {
  description = "Name of the S3 bucket for data ingestion"
  type        = string
  default     = null
}

variable "enable_versioning" {
  description = "Enable versioning on the S3 bucket"
  type        = bool
  default     = true
}

variable "force_destroy_bucket" {
  description = "Allow deletion of non-empty bucket (useful for development)"
  type        = bool
  default     = false
}

variable "opensearch_domain_name" {
  description = "Name of the OpenSearch domain"
  type        = string
  default     = "opensearch-ingest-domain"
}

variable "opensearch_instance_count" {
  description = "Number of instances in the OpenSearch cluster"
  type        = number
  default     = 1
}

variable "opensearch_instance_type" {
  description = "Instance type for OpenSearch cluster nodes"
  type        = string
  default     = "m8g.large.search"
}

variable "opensearch_version" {
  description = "OpenSearch engine version"
  type        = string
  default     = "OpenSearch_2.19"
}

variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default = {
    Environment = "dev"
    Project     = "opensearch-ingest"
    ManagedBy   = "terraform"
  }
}