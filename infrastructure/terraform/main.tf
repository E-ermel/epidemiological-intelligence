resource "google_storage_bucket" "data_lake" {
  name     = var.bucket_name
  location = var.region

  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  public_access_prevention = "enforced"
  force_destroy            = false
}
resource "google_bigquery_dataset" "analytics" {
  dataset_id    = "epidemiological_intelligence"
  friendly_name = "Epidemiological Intelligence"
  description   = "Analytical dataset"

  location = "US"

  delete_contents_on_destroy = false
}
resource "google_service_account" "databricks" {
  account_id   = "databricks-epidemiology"
  display_name = "Databricks Epidemiology"
  description  = "Service account used by Databricks to access the epidemiological data platform"
}
resource "google_storage_bucket_iam_member" "databricks_bucket_access" {
  bucket = google_storage_bucket.data_lake.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.databricks.email}"
}

resource "google_project_iam_member" "databricks_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.databricks.email}"
}
resource "google_bigquery_dataset_iam_member" "databricks_dataset_access" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.databricks.email}"
}