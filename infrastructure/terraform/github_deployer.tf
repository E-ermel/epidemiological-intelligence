# ============================================================
# github-deployer - dedicated CI/CD identity
#
# Used only by GitHub Actions to push Docker images and deploy new
# Cloud Run revisions. Deliberately separate from the runtime Service
# Accounts (epidemiological-ai-sa, epidemiological-de-sa,
# epidemiological-ds-job, airflow-orchestrator) so a compromised CI
# pipeline cannot act as any of those.
#
# This SA does NOT have permission to run `terraform apply` -- see the
# CD infra report for why that was deliberately left out and what the
# safer alternative is.
# ============================================================

resource "google_service_account" "github_deployer" {
  project = var.project_id

  account_id   = "github-deployer"
  display_name = "GitHub Actions Deployer"
  description  = "CI/CD identity used by GitHub Actions via Workload Identity Federation. Not a runtime identity."

  depends_on = [
    google_project_service.iam_api
  ]
}

# ------------------------------------------------------------
# A) Who can impersonate github-deployer: only the OIDC identity
#    minted for this exact GitHub repository.
# ------------------------------------------------------------

resource "google_service_account_iam_member" "github_deployer_wif_binding" {
  service_account_id = google_service_account.github_deployer.name
  role               = "roles/iam.workloadIdentityUser"

  member = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_actions.name}/attribute.repository/E-ermel/epidemiological-intelligence"
}

# ------------------------------------------------------------
# B) What github-deployer can do inside GCP, once impersonated.
#    Least privilege: push images + deploy existing Cloud Run
#    resources. No project-wide roles, no Owner/Editor.
# ------------------------------------------------------------

# Push images: Artifact Registry writer, scoped per repository (not
# project-wide artifactregistry.writer).

resource "google_artifact_registry_repository_iam_member" "github_deployer_ar_de" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.de.repository_id

  role   = "roles/artifactregistry.writer"
  member = "serviceAccount:${google_service_account.github_deployer.email}"
}

resource "google_artifact_registry_repository_iam_member" "github_deployer_ar_ds" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.data_science.repository_id

  role   = "roles/artifactregistry.writer"
  member = "serviceAccount:${google_service_account.github_deployer.email}"
}

resource "google_artifact_registry_repository_iam_member" "github_deployer_ar_ai" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.ai.repository_id

  role   = "roles/artifactregistry.writer"
  member = "serviceAccount:${google_service_account.github_deployer.email}"
}

# Deploy new revisions: run.developer scoped per Cloud Run resource
# (not project-wide run.admin/run.developer). Includes updating the
# image and creating revisions, not deleting services/jobs or changing
# their IAM policy.

resource "google_cloud_run_v2_service_iam_member" "github_deployer_ai_run_developer" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ai.name

  role   = "roles/run.developer"
  member = "serviceAccount:${google_service_account.github_deployer.email}"
}

resource "google_cloud_run_v2_job_iam_member" "github_deployer_de_run_developer" {
  for_each = google_cloud_run_v2_job.de

  project  = var.project_id
  location = var.region
  name     = each.value.name

  role   = "roles/run.developer"
  member = "serviceAccount:${google_service_account.github_deployer.email}"
}

resource "google_cloud_run_v2_job_iam_member" "github_deployer_ds_run_developer" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.data_science.name

  role   = "roles/run.developer"
  member = "serviceAccount:${google_service_account.github_deployer.email}"
}

# Deploying a Cloud Run revision that runs as a given runtime SA
# requires actAs on that SA (roles/iam.serviceAccountUser). This grants
# github-deployer that, and nothing else, on each runtime SA -- it does
# NOT let github-deployer manage those SAs' own IAM policies or keys.

resource "google_service_account_iam_member" "github_deployer_actas_ai" {
  service_account_id = google_service_account.ai.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_deployer.email}"
}

resource "google_service_account_iam_member" "github_deployer_actas_de" {
  service_account_id = google_service_account.de.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_deployer.email}"
}

resource "google_service_account_iam_member" "github_deployer_actas_ds" {
  service_account_id = google_service_account.data_science_job.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_deployer.email}"
}
