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

output "github_actions_workload_identity_provider" {
  description = "Full resource name for the workload_identity_provider input of google-github-actions/auth"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "github_deployer_service_account_email" {
  description = "Email for the service_account input of google-github-actions/auth"
  value       = google_service_account.github_deployer.email
}
