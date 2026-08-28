# ============================================================
# Workload Identity Federation - GitHub Actions
#
# Lets GitHub Actions authenticate to GCP by exchanging a GitHub-issued
# OIDC token for a short-lived GCP access token. No Service Account
# JSON key is created or stored anywhere.
# ============================================================

resource "google_iam_workload_identity_pool" "github_actions" {
  project                   = var.project_id
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions"
  description               = "Identity pool for GitHub Actions OIDC federation"

  depends_on = [
    google_project_service.iam_api,
    google_project_service.sts_api,
  ]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_actions.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub OIDC Provider"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
  }

  # Rejects the token exchange itself for any repository other than this
  # one, before the resulting identity ever reaches an IAM check. See the
  # CD infra report for how this differs from (and complements) the
  # principalSet restriction on the github-deployer Service Account.
  attribute_condition = "assertion.repository == \"E-ermel/epidemiological-intelligence\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  depends_on = [
    google_iam_workload_identity_pool.github_actions,
    google_project_service.iamcredentials_api,
  ]
}
