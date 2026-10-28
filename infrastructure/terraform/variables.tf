variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region used for regional resources"
  type        = string
  default     = "us-central1"
}

variable "ingest_region" {
  description = "Region for the source -> bronze ingestion jobs. Brazilian government endpoints (IBGE, DATASUS, INMET) time out from US regions (geo-blocking), so these jobs run in Brazil."
  type        = string
  default     = "southamerica-east1"
}

variable "bucket_name" {
  description = "Data Lake bucket name"
  type        = string
}

variable "de_repository_id" {
  description = "Artifact Registry repository for Data Engineering"
  type        = string
}

variable "de_image_name" {
  description = "Docker image name for Data Engineering"
  type        = string
  default     = "epidemiological-de"
}

variable "de_image_tag" {
  description = "Docker image tag for Data Engineering"
  type        = string
  default     = "latest"
}

variable "ai_image" {
  description = "Full Artifact Registry image path for the AI service"
  type        = string
}

variable "bigquery_dataset_id" {
  description = "BigQuery dataset containing the Gold tables"
  type        = string
  default     = "epidemiological_intelligence"
}

variable "bigquery_gold_table" {
  description = "Gold table consumed by the AI service and the Data Science pipeline (national gold)"
  type        = string
  default     = "epidemiology_climate_monthly_br"
}

variable "data_science_image" {
  description = "Docker image used by the Data Science Cloud Run Job"
  type        = string
}