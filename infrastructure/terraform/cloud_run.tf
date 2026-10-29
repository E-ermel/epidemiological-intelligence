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
  lifecycle {
    # client/client_version são reescritos a cada `gcloud run jobs
    # update` do workflow Deploy -- não são gerenciados aqui.
    ignore_changes = [
      template[0].template[0].containers[0].image,
      client,
      client_version,
    ]
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
  # region: os jobs de ingestão (fonte -> bronze) rodam no Brasil porque
  # IBGE/DATASUS/INMET não respondem a conexões vindas dos EUA
  # (bloqueio geográfico, confirmado com curl a partir do Cloud Run). Os
  # de transformação ficam junto do resto, em var.region.
  #
  # task_count/parallelism (opcionais): jobs por UF dividem o país
  # entre tasks (CLOUD_RUN_TASK_INDEX); os demais rodam numa task só.
  de_job_defaults = {
    task_count  = 1
    parallelism = null
  }

  de_jobs = { for name, job in local.de_job_specs : name => merge(local.de_job_defaults, job) }

  de_job_specs = {
    inmet = {
      module = "epidemiological_de.inmet.pipeline"
      region = var.region
    }

    sinan = {
      module = "epidemiological_de.sinan.pipeline"
      region = var.region
    }

    gold = {
      module = "epidemiological_de.gold.pipeline"
      region = var.region
    }

    # Ingestão (fonte -> bronze) separada da transformação: pode ser
    # repetida sem reprocessar o silver, e vice-versa.
    ibge-ingest = {
      module = "epidemiological_de.ibge.ingest"
      region = var.ingest_region
    }

    ibge = {
      module = "epidemiological_de.ibge.pipeline"
      region = var.region
    }

    inmet-ingest = {
      module = "epidemiological_de.inmet.ingest"
      region = var.ingest_region
    }

    # Uma task por UF. Paralelismo limitado para não abrir 27 conexões
    # simultâneas no FTP do DATASUS.
    sih-ingest = {
      module      = "epidemiological_de.sih.ingest"
      region      = var.ingest_region
      task_count  = 27
      parallelism = 9
    }

    # Um arquivo nacional por agravo/ano, ~200 MB no total: uma task.
    sinan-ingest = {
      module = "epidemiological_de.sinan.ingest"
      region = var.ingest_region
    }

    sidra-ingest = {
      module = "epidemiological_de.sidra.ingest"
      region = var.ingest_region
    }

    sidra = {
      module = "epidemiological_de.sidra.pipeline"
      region = var.region
    }

    # Consulta a cópia do Atlas na Base dos Dados (BigQuery): sem
    # bloqueio geográfico, roda junto do resto.
    atlas-ingest = {
      module = "epidemiological_de.atlas.ingest"
      region = var.region
    }

    atlas = {
      module = "epidemiological_de.atlas.pipeline"
      region = var.region
    }

    # Cópia do MapBiomas na Base dos Dados (BigQuery), como o Atlas.
    mapbiomas-ingest = {
      module = "epidemiological_de.mapbiomas.ingest"
      region = var.region
    }

    mapbiomas = {
      module = "epidemiological_de.mapbiomas.pipeline"
      region = var.region
    }

    # Arquivos do dashboard PRODES (TerraBrasilis/INPE), servidor do
    # governo: ingestão no Brasil, como as demais.
    prodes-ingest = {
      module = "epidemiological_de.prodes.ingest"
      region = var.ingest_region
    }

    prodes = {
      module = "epidemiological_de.prodes.pipeline"
      region = var.region
    }

    # Silver do SIH: uma task por UF, lendo o bronze no GCS.
    sih = {
      module     = "epidemiological_de.sih.pipeline"
      region     = var.region
      task_count = 27
    }
  }

  de_image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.de_repository_id}/${var.de_image_name}:${var.de_image_tag}"
}

resource "google_cloud_run_v2_job" "de" {
  for_each = local.de_jobs

  project  = var.project_id
  name     = "epidemiological-de-${each.key}"
  location = each.value.region

  deletion_protection = false

  template {
    task_count  = each.value.task_count
    parallelism = each.value.parallelism

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
  lifecycle {
    # client/client_version são reescritos a cada `gcloud run jobs
    # update` do workflow Deploy -- não são gerenciados aqui.
    ignore_changes = [
      template[0].template[0].containers[0].image,
      client,
      client_version,
    ]
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
        name  = "GCP_REGION"
        value = var.region
      }

      env {
        name  = "DS_JOB_NAME"
        value = google_cloud_run_v2_job.data_science.name
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

      # O chat, os filtros e o retrain chamam a API direto do navegador;
      # sem isso o CORS do app.py só libera http://localhost:3000.
      env {
        name  = "ALLOWED_ORIGINS"
        value = local.frontend_origins
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

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
      scaling,
    ]
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
