resource "google_artifact_registry_repository" "de" {
  location      = var.region
  repository_id = var.de_repository_id
  description   = "Docker images for Epidemiological Intelligence Data Engineering"
  format        = "DOCKER"
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

  depends_on = [
    google_project_service.artifact_registry_api
  ]
}

resource "google_service_account" "ai" {
  account_id   = "epidemiological-ai-sa"
  display_name = "Epidemiological Intelligence AI"

  depends_on = [
    google_project_service.iam_api
  ]
}