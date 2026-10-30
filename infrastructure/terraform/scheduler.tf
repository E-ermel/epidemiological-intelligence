# ============================================================
# Cloud Scheduler - execução mensal do pipeline
#
# Dispara o workflow epidemiological-pipeline todo mês (var.pipeline_schedule,
# dia 1, às 3h): ingestão -> silver ->
# gold -> alerta de surtos. Fontes que não mudaram viram no-op.
# Começa pausado (var.pipeline_schedule_paused); para ativar, defina a
# variável como false e rode terraform apply.
# ============================================================

resource "google_project_service" "cloud_scheduler_api" {
  project = var.project_id
  service = "cloudscheduler.googleapis.com"

  disable_on_destroy = false
}

resource "google_service_account" "pipeline_scheduler" {
  account_id   = "epidemiological-pipeline-sched"
  display_name = "Epidemiological Pipeline Scheduler"

  depends_on = [
    google_project_service.iam_api
  ]
}

# workflows.invoker só no projeto: não há binding por workflow.
resource "google_project_iam_member" "pipeline_scheduler_invoker" {
  project = var.project_id
  role    = "roles/workflows.invoker"

  member = "serviceAccount:${google_service_account.pipeline_scheduler.email}"
}

resource "google_cloud_scheduler_job" "pipeline_monthly" {
  project   = var.project_id
  name      = "epidemiological-pipeline-monthly"
  region    = var.region
  schedule  = var.pipeline_schedule
  time_zone = "America/Sao_Paulo"
  paused    = var.pipeline_schedule_paused

  # O workflow leva horas na primeira execução; o Scheduler só cria a
  # execução (a chamada retorna na hora), não espera ela terminar.
  attempt_deadline = "60s"

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://workflowexecutions.googleapis.com/v1/${google_workflows_workflow.pipeline.id}/executions"
    body        = base64encode(jsonencode({ argument = "{}" }))

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.pipeline_scheduler.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  depends_on = [
    google_project_service.cloud_scheduler_api,
    google_project_iam_member.pipeline_scheduler_invoker,
  ]
}
