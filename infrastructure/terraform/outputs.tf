output "databricks_service_account_email" {
  description = "Service account used by Databricks"
  value       = google_service_account.databricks.email
}