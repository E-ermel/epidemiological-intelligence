# Limpeza de imagens antigas, igual nos três repositórios: cada imagem
# guarda as 5 versões mais recentes (inclui a que está no ar); as demais
# são apagadas depois de 7 dias. KEEP tem precedência sobre DELETE.
locals {
  image_cleanup_policies = [
    { id = "keep-5-most-recent", action = "KEEP", keep_count = 5, older_than = null },
    { id = "delete-older-than-7-days", action = "DELETE", keep_count = null, older_than = "604800s" },
  ]
}

resource "google_artifact_registry_repository" "de" {
  location      = var.region
  repository_id = var.de_repository_id
  description   = "Docker images for Epidemiological Intelligence Data Engineering"
  format        = "DOCKER"

  cleanup_policy_dry_run = false

  dynamic "cleanup_policies" {
    for_each = local.image_cleanup_policies
    content {
      id     = cleanup_policies.value.id
      action = cleanup_policies.value.action

      dynamic "condition" {
        for_each = cleanup_policies.value.older_than == null ? [] : [1]
        content {
          tag_state  = "ANY"
          older_than = cleanup_policies.value.older_than
        }
      }

      dynamic "most_recent_versions" {
        for_each = cleanup_policies.value.keep_count == null ? [] : [1]
        content {
          keep_count = cleanup_policies.value.keep_count
        }
      }
    }
  }
}

resource "google_project_service" "artifact_registry_api" {
  project = var.project_id
  service = "artifactregistry.googleapis.com"

  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "data_science" {
  project       = var.project_id
  location      = var.region
  repository_id = "epidemiological-ds"
  description   = "Docker images for epidemiological Data Science jobs"
  format        = "DOCKER"

  cleanup_policy_dry_run = false

  dynamic "cleanup_policies" {
    for_each = local.image_cleanup_policies
    content {
      id     = cleanup_policies.value.id
      action = cleanup_policies.value.action

      dynamic "condition" {
        for_each = cleanup_policies.value.older_than == null ? [] : [1]
        content {
          tag_state  = "ANY"
          older_than = cleanup_policies.value.older_than
        }
      }

      dynamic "most_recent_versions" {
        for_each = cleanup_policies.value.keep_count == null ? [] : [1]
        content {
          keep_count = cleanup_policies.value.keep_count
        }
      }
    }
  }

  depends_on = [
    google_project_service.artifact_registry_api
  ]
}

resource "google_artifact_registry_repository" "ai" {
  project       = var.project_id
  location      = var.region
  repository_id = "epidemiological-intelligence"
  description   = "Docker images for the Epidemiological Intelligence AI service"
  format        = "DOCKER"

  cleanup_policy_dry_run = false

  dynamic "cleanup_policies" {
    for_each = local.image_cleanup_policies
    content {
      id     = cleanup_policies.value.id
      action = cleanup_policies.value.action

      dynamic "condition" {
        for_each = cleanup_policies.value.older_than == null ? [] : [1]
        content {
          tag_state  = "ANY"
          older_than = cleanup_policies.value.older_than
        }
      }

      dynamic "most_recent_versions" {
        for_each = cleanup_policies.value.keep_count == null ? [] : [1]
        content {
          keep_count = cleanup_policies.value.keep_count
        }
      }
    }
  }

  # This repository was created manually and already exists in GCP.
  # It must be imported into state before the first `terraform apply`
  # that includes this resource, or apply will fail with "already exists".
  # See the CD infra report for the exact `terraform import` command.
}

resource "google_service_account" "ai" {
  account_id   = "epidemiological-ai-sa"
  display_name = "Epidemiological Intelligence AI"

  depends_on = [
    google_project_service.iam_api
  ]
}