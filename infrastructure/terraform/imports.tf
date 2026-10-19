# ============================================================
# Reconstrução do state (perdido ao formatar o computador)
#
# Recursos que já existem no GCP e dariam "already exists" num apply.
# Os *_iam_member e google_project_service NÃO estão aqui de propósito:
# criá-los de novo é idempotente (o GCP só confirma o binding/API que
# já existe), então o apply os recoloca no state sem conflito.
#
# Depois do primeiro `terraform apply` bem-sucedido este arquivo pode
# ser apagado -- import blocks já aplicados viram no-op.
# ============================================================

# --- Storage / BigQuery / Secret Manager --------------------

import {
  to = google_storage_bucket.data_lake
  id = var.bucket_name
}

import {
  to = google_bigquery_dataset.analytics
  id = "projects/${var.project_id}/datasets/${var.bigquery_dataset_id}"
}

import {
  to = google_secret_manager_secret.openai_api_key
  id = "projects/${var.project_id}/secrets/openai-api-key"
}

# --- Service Accounts ---------------------------------------

import {
  to = google_service_account.ai
  id = "projects/${var.project_id}/serviceAccounts/epidemiological-ai-sa@${var.project_id}.iam.gserviceaccount.com"
}

import {
  to = google_service_account.de
  id = "projects/${var.project_id}/serviceAccounts/epidemiological-de-sa@${var.project_id}.iam.gserviceaccount.com"
}

import {
  to = google_service_account.data_science_job
  id = "projects/${var.project_id}/serviceAccounts/epidemiological-ds-job@${var.project_id}.iam.gserviceaccount.com"
}

import {
  to = google_service_account.github_deployer
  id = "projects/${var.project_id}/serviceAccounts/github-deployer@${var.project_id}.iam.gserviceaccount.com"
}

import {
  to = google_service_account.airflow_orchestrator
  id = "projects/${var.project_id}/serviceAccounts/airflow-orchestrator@${var.project_id}.iam.gserviceaccount.com"
}

# --- Artifact Registry --------------------------------------

import {
  to = google_artifact_registry_repository.ai
  id = "projects/${var.project_id}/locations/${var.region}/repositories/epidemiological-intelligence"
}

import {
  to = google_artifact_registry_repository.de
  id = "projects/${var.project_id}/locations/${var.region}/repositories/${var.de_repository_id}"
}

import {
  to = google_artifact_registry_repository.data_science
  id = "projects/${var.project_id}/locations/${var.region}/repositories/epidemiological-ds"
}

# --- Cloud Run ----------------------------------------------

import {
  to = google_cloud_run_v2_service.ai
  id = "projects/${var.project_id}/locations/${var.region}/services/epidemiological-ai"
}

import {
  to = google_cloud_run_v2_job.data_science
  id = "projects/${var.project_id}/locations/${var.region}/jobs/epidemiological-ds-modeling"
}

import {
  for_each = local.de_jobs

  to = google_cloud_run_v2_job.de[each.key]
  id = "projects/${var.project_id}/locations/${var.region}/jobs/epidemiological-de-${each.key}"
}

# --- Workload Identity Federation (GitHub Actions) ----------

import {
  to = google_iam_workload_identity_pool.github_actions
  id = "projects/${var.project_id}/locations/global/workloadIdentityPools/github-actions-pool"
}

import {
  to = google_iam_workload_identity_pool_provider.github
  id = "projects/${var.project_id}/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider"
}
