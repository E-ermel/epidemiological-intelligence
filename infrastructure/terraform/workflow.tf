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
    ibge_ingest      = google_cloud_run_v2_job.de["ibge-ingest"]
    inmet_ingest     = google_cloud_run_v2_job.de["inmet-ingest"]
    sih_ingest       = google_cloud_run_v2_job.de["sih-ingest"]
    sinan_ingest     = google_cloud_run_v2_job.de["sinan-ingest"]
    sidra_ingest     = google_cloud_run_v2_job.de["sidra-ingest"]
    sidra            = google_cloud_run_v2_job.de["sidra"]
    atlas_ingest     = google_cloud_run_v2_job.de["atlas-ingest"]
    atlas            = google_cloud_run_v2_job.de["atlas"]
    mapbiomas_ingest = google_cloud_run_v2_job.de["mapbiomas-ingest"]
    mapbiomas        = google_cloud_run_v2_job.de["mapbiomas"]
    ibge             = google_cloud_run_v2_job.de["ibge"]
    inmet            = google_cloud_run_v2_job.de["inmet"]
    sih              = google_cloud_run_v2_job.de["sih"]
    sinan            = google_cloud_run_v2_job.de["sinan"]
    gold             = google_cloud_run_v2_job.de["gold"]
    ds               = google_cloud_run_v2_job.data_science
  }
}

# run.developer só em cada job do pipeline (disparar e acompanhar a
# execução), não no projeto inteiro como era o airflow_run_developer.
resource "google_cloud_run_v2_job_iam_member" "pipeline_workflow_run_developer" {
  for_each = local.pipeline_jobs

  project  = var.project_id
  location = each.value.location
  name     = each.value.name

  role   = "roles/run.developer"
  member = "serviceAccount:${google_service_account.pipeline_workflow.email}"
}

resource "google_workflows_workflow" "pipeline" {
  project         = var.project_id
  name            = "epidemiological-pipeline"
  region          = var.region
  description     = "ingestao (ibge, inmet, sih, sinan, sidra, atlas, mapbiomas) -> ibge -> silver de cada fonte -> gold nacional (+ BigQuery)"
  service_account = google_service_account.pipeline_workflow.id

  # job.id = "projects/<p>/locations/<r>/jobs/<nome>", o formato que o
  # conector espera em `name`.
  source_contents = templatefile("${path.module}/workflows/pipeline.yaml", {
    for key, job in local.pipeline_jobs : "${key}_job" => job.id
  })

  depends_on = [
    google_project_service.workflows_api,
    google_cloud_run_v2_job_iam_member.pipeline_workflow_run_developer,
    google_project_iam_member.pipeline_workflow_run_viewer,
  ]

}

# O conector jobs.run acompanha a execução consultando a operação de
# longa duração (projects/<p>/locations/<r>/operations/<id>), e
# run.operations.get só existe no nível do projeto -- não dá para
# conceder por job. run.viewer é só leitura (get/list); disparar os
# jobs continua restrito aos 4 bindings por job acima.
resource "google_project_iam_member" "pipeline_workflow_run_viewer" {
  project = var.project_id
  role    = "roles/run.viewer"

  member = "serviceAccount:${google_service_account.pipeline_workflow.email}"
}
