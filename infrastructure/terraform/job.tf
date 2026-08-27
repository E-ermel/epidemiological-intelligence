resource "google_project_service" "cloud_run_api" {
  project = var.project_id
  service = "run.googleapis.com"

  disable_on_destroy = false
}


resource "google_cloud_run_v2_job" "data_science" {
  project  = var.project_id
  name     = "epidemiological-ds-modeling"
  location = var.region

  deletion_protection = false

  template {
    template {
      service_account = google_service_account.data_science_job.email

      timeout     = "3600s"
      max_retries = 1

      containers {
        image = var.data_science_image

        resources {
          limits = {
            cpu    = "2"
            memory = "4Gi"
          }
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "BIGQUERY_DATASET"
          value = var.bigquery_dataset_id
        }

        env {
          name  = "BIGQUERY_GOLD_TABLE"
          value = var.bigquery_gold_table
        }

        env {
            name  = "ARTIFACT_BUCKET"
            value = var.bucket_name
            }

        env {
          name  = "MODEL_ARTIFACT_PREFIX"
          value = "modeling"
        }
      }
    }
  }

  depends_on = [
    google_project_service.cloud_run_api,
    google_artifact_registry_repository.data_science,
    google_project_iam_member.ds_bigquery_job_user,
    google_bigquery_dataset_iam_member.ds_bigquery_data_viewer,
    google_storage_bucket_iam_member.ds_artifact_writer
  ]
}