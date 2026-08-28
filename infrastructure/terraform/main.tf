resource "google_storage_bucket" "data_lake" {
  name     = var.bucket_name
  location = var.region

  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  public_access_prevention = "enforced"
  force_destroy            = false
}
resource "google_bigquery_dataset" "analytics" {
  dataset_id    = "epidemiological_intelligence"
  friendly_name = "Epidemiological Intelligence"
  description   = "Analytical dataset"

  location = "US"

  delete_contents_on_destroy = false
}
