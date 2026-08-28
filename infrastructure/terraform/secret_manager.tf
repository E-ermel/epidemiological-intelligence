resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "openai-api-key"

  replication {
    auto {}
  }
}