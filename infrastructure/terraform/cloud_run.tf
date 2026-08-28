resource "google_project_service" "cloud_run_api" {
  project = var.project_id
  service = "run.googleapis.com"

  disable_on_destroy = false
}

# ============================================================
# Cloud Run Job - Data Science
# ============================================================
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

# ============================================================
# Cloud Run Jobs - Data Engineering
# ============================================================
locals {
  de_jobs = {
    inmet = {
      module = "epidemiological_de.inmet.pipeline"
    }

    sinan = {
      module = "epidemiological_de.sinan.pipeline"
    }

    gold = {
      module = "epidemiological_de.gold.pipeline"
    }
  }

  de_image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.de_repository_id}/${var.de_image_name}:${var.de_image_tag}"
}

resource "google_cloud_run_v2_job" "de" {
  for_each = local.de_jobs

  project  = var.project_id
  name     = "epidemiological-de-${each.key}"
  location = var.region

  deletion_protection = false

  template {
    template {
      service_account = google_service_account.de.email

      timeout     = "3600s"
      max_retries = 1

      containers {
        image = local.de_image

        command = ["python"]
        args    = ["-m", each.value.module]

        resources {
          limits = {
            cpu    = "2"
            memory = "4Gi"
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.cloud_run_api,
    google_artifact_registry_repository.de,
    google_storage_bucket_iam_member.de_storage_editor
  ]
}

# ============================================================
# Cloud Run Service - AI Agent
# ============================================================
resource "google_cloud_run_v2_service" "ai" {
  project  = var.project_id
  name     = "epidemiological-ai"
  location = var.region

  deletion_protection = false

  template {
    service_account = google_service_account.ai.email

    containers {
      image = var.ai_image

      ports {
        container_port = 8080
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

      env {
        name = "OPENAI_API_KEY"

        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openai_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.cloud_run_api,
    google_project_iam_member.ai_bigquery_job_user,
    google_storage_bucket_iam_member.ai_storage_viewer,
    google_bigquery_dataset_iam_member.ai_bigquery_viewer,
    google_secret_manager_secret_iam_member.ai_openai_secret
  ]
}

# ============================================================
# Public access - AI Agent
# ============================================================
resource "google_cloud_run_v2_service_iam_member" "ai_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ai.name

  role   = "roles/run.invoker"
  member = "allUsers"
}
