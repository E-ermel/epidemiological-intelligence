resource "google_service_account" "data_science_job" {
  project = var.project_id

  account_id   = "epidemiological-ds-job"
  display_name = "Epidemiological Data Science Job"
  description  = "Service account used by the Data Science Cloud Run Job"

  depends_on = [
    google_project_service.iam_api
  ]
}