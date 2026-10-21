# ============================================================
# Cloud Workflows - orquestração do pipeline
#
# Substitui o Airflow: inmet + sinan (em paralelo) -> gold (que
# também carrega o BigQuery) -> modelagem.
# Execução manual: gcloud workflows run epidemiological-pipeline --location=us-central1
# ============================================================

resource "google_service_account" "pipeline_workflow" {
  account_id   = "epidemiological-pipeline-wf"
  display_name = "Epidemiological Pipeline Workflow"

  depends_on = [
    google_project_service.iam_api
  ]
}

locals {
  pipeline_jobs = {
    inmet = google_cloud_run_v2_job.de["inmet"]
    sinan = google_cloud_run_v2_job.de["sinan"]
    gold  = google_cloud_run_v2_job.de["gold"]
    ds    = google_cloud_run_v2_job.data_science
  }
}

# run.developer só em cada job do pipeline (disparar e acompanhar a
# execução), não no projeto inteiro como era o airflow_run_developer.
resource "google_cloud_run_v2_job_iam_member" "pipeline_workflow_run_developer" {
  for_each = local.pipeline_jobs

  project  = var.project_id
  location = var.region
  name     = each.value.name

  role   = "roles/run.developer"
  member = "serviceAccount:${google_service_account.pipeline_workflow.email}"
}

resource "google_workflows_workflow" "pipeline" {
  project         = var.project_id
  name            = "epidemiological-pipeline"
  region          = var.region
  description     = "inmet + sinan -> gold (+ BigQuery) -> modelagem"
  service_account = google_service_account.pipeline_workflow.id

  # job.id = "projects/<p>/locations/<r>/jobs/<nome>", o formato que o
  # conector espera em `name`.
  source_contents = templatefile("${path.module}/workflows/pipeline.yaml", {
    for key, job in local.pipeline_jobs : "${key}_job" => job.id
  })

  depends_on = [
    google_project_service.workflows_api,
    google_cloud_run_v2_job_iam_member.pipeline_workflow_run_developer,
  ]
}
