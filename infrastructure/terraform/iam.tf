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

# storage.objects.list is checked against the *bucket* resource, not an
# object -- an object-name-prefixed condition (like ds_artifact_writer
# above) never covers it, no matter the prefix. Without this, every
# retrain fails at get_next_version() (which lists modeling/<disease>/
# to pick the next version number) with a 403 on storage.objects.list.
# Same unconditional-objectViewer pattern already used below for
# airflow_orchestrator and ai.
resource "google_storage_bucket_iam_member" "ds_artifact_reader" {
  bucket = var.bucket_name
  role   = "roles/storage.objectViewer"

  member = "serviceAccount:${google_service_account.data_science_job.email}"
}


resource "google_project_iam_member" "airflow_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"

  member = "serviceAccount:${google_service_account.airflow_orchestrator.email}"
}


resource "google_storage_bucket_iam_member" "airflow_gcs_reader" {
  bucket = var.bucket_name
  role   = "roles/storage.objectViewer"

  member = "serviceAccount:${google_service_account.airflow_orchestrator.email}"
}


resource "google_bigquery_dataset_iam_member" "airflow_bq_data_editor" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.analytics.dataset_id

  role = "roles/bigquery.dataEditor"

  member = "serviceAccount:${google_service_account.airflow_orchestrator.email}"
}


resource "google_project_iam_member" "airflow_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"

  member = "serviceAccount:${google_service_account.airflow_orchestrator.email}"
}

resource "google_service_account_iam_member" "airflow_impersonation" {
  service_account_id = google_service_account.airflow_orchestrator.name
  role               = "roles/iam.serviceAccountTokenCreator"

  member = "user:eduardoermel@gmail.com"
}

resource "google_service_account" "de" {
  account_id   = "epidemiological-de-sa"
  display_name = "Epidemiological Intelligence Data Engineering"

  depends_on = [
    google_project_service.iam_api
  ]
}

resource "google_storage_bucket_iam_member" "de_storage_editor" {
  bucket = var.bucket_name
  role   = "roles/storage.objectUser"

  member = "serviceAccount:${google_service_account.de.email}"
}
resource "google_project_iam_member" "ai_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"

  member = "serviceAccount:${google_service_account.ai.email}"
}
resource "google_storage_bucket_iam_member" "ai_storage_viewer" {
  bucket = var.bucket_name
  role   = "roles/storage.objectViewer"

  member = "serviceAccount:${google_service_account.ai.email}"
}
resource "google_bigquery_dataset_iam_member" "ai_bigquery_viewer" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id

  role = "roles/bigquery.dataViewer"

  member = "serviceAccount:${google_service_account.ai.email}"
}
resource "google_secret_manager_secret_iam_member" "ai_openai_secret" {
  secret_id = google_secret_manager_secret.openai_api_key.id

  role = "roles/secretmanager.secretAccessor"

  member = "serviceAccount:${google_service_account.ai.email}"
}

# Lets the "Retreinar modelo" button (POST /models/{disease}/retrain)
# start an execution of the data_science job -- scoped to just that
# job, not project-wide run.developer, same reasoning as
# github_deployer's per-resource grants in github_deployer.tf.
resource "google_cloud_run_v2_job_iam_member" "ai_ds_job_run_developer" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.data_science.name

  role   = "roles/run.developer"
  member = "serviceAccount:${google_service_account.ai.email}"
}