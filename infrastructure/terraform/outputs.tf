output "databricks_service_account_email" {
  description = "Service account used by Databricks"
  value       = google_service_account.databricks.email
}
output "data_science_service_account" {
  description = "Service account used by the Data Science job"
  value       = google_service_account.data_science_job.email
}

output "data_science_artifact_registry" {
  description = "Artifact Registry repository for the Data Science image"
  value       = google_artifact_registry_repository.data_science.name
}

output "data_science_cloud_run_job" {
  description = "Cloud Run Job responsible for model execution"
  value       = google_cloud_run_v2_job.data_science.name
}
