resource "google_storage_bucket" "data_lake"{
    name     = var.bucket_name
    location = var.region

    storage_class = "STANDARD"

    uniform_bucket_level_access = true

    public_access_prevention = "enforced"
}