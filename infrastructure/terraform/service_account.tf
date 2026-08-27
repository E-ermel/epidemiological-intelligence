resource "google_service_account" "airflow_orchestrator" {
  project = var.project_id

  account_id   = "airflow-orchestrator"
  display_name = "Airflow Orchestrator"
  description  = "Service account used by Airflow to trigger BigQuery loads and Cloud Run jobs"
}
