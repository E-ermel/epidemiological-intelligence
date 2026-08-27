resource "google_project_iam_member" "ds_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"

  member = "serviceAccount:${google_service_account.data_science_job.email}"
}


resource "google_bigquery_dataset_iam_member" "ds_bigquery_data_viewer" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.analytics.dataset_id

  role = "roles/bigquery.dataViewer"

  member = "serviceAccount:${google_service_account.data_science_job.email}"
}


resource "google_storage_bucket_iam_member" "ds_artifact_writer" {
  bucket = var.bucket_name
  role   = "roles/storage.objectAdmin"

  member = "serviceAccount:${google_service_account.data_science_job.email}"

  condition {
    title       = "ds_modeling_artifacts_only"
    description = "Restrict write access to the modeling artifact prefix"
    expression  = "resource.name.startsWith(\"projects/_/buckets/${var.bucket_name}/objects/modeling/\")"
  }
}