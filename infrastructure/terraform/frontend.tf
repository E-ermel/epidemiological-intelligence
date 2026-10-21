# ============================================================
# Cloud Run Service - Frontend (Next.js)
#
# A imagem é publicada pelo workflow Deploy (component: frontend) no
# mesmo repositório do Artifact Registry da IA
# ("epidemiological-intelligence"), onde github-deployer já tem
# artifactregistry.writer -- por isso não há repositório novo aqui.
# ============================================================

# Identidade de runtime própria, sem nenhum papel: o frontend só faz
# HTTP para a API pública, então não precisa de acesso a GCS/BigQuery.
# Evita cair na default compute SA, que costuma ter Editor no projeto.
resource "google_service_account" "frontend" {
  account_id   = "epidemiological-frontend-sa"
  display_name = "Epidemiological Intelligence Frontend"

  depends_on = [
    google_project_service.iam_api
  ]
}

resource "google_cloud_run_v2_service" "frontend" {
  project  = var.project_id
  name     = "epidemiological-frontend"
  location = var.region

  deletion_protection = false

  template {
    service_account = google_service_account.frontend.email

    containers {
      # Placeholder só para a criação do serviço: a imagem real ainda
      # não existe antes do primeiro deploy, e o workflow é quem troca a
      # imagem depois (ignore_changes abaixo).
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = 8080
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
    google_project_service.cloud_run_api
  ]
}

# Todo serviço Cloud Run responde em duas URLs (a com hash, *.a.run.app,
# e a determinística <nome>-<número do projeto>.<região>.run.app), e o
# navegador manda como Origin a que o usuário abriu -- as duas precisam
# estar no ALLOWED_ORIGINS da API (cloud_run.tf).
data "google_project" "current" {
  project_id = var.project_id
}

locals {
  frontend_origins = join(",", distinct([
    google_cloud_run_v2_service.frontend.uri,
    "https://${google_cloud_run_v2_service.frontend.name}-${data.google_project.current.number}.${var.region}.run.app",
  ]))
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend.name

  role   = "roles/run.invoker"
  member = "allUsers"
}

# Mesmo padrão de github_deployer.tf: run.developer só neste serviço e
# actAs só na SA de runtime dele.
resource "google_cloud_run_v2_service_iam_member" "github_deployer_frontend_run_developer" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend.name

  role   = "roles/run.developer"
  member = "serviceAccount:${google_service_account.github_deployer.email}"
}

resource "google_service_account_iam_member" "github_deployer_actas_frontend" {
  service_account_id = google_service_account.frontend.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_deployer.email}"
}
