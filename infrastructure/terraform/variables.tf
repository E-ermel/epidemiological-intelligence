variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Main resourses region"
  type        = string
  default     = "us-central"
}
variable "bucket_name" {
  description = "Data Lake bucket name"
  type        = string
}