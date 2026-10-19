terraform {
  # 1.7+: imports.tf usa import com for_each e ids com variáveis.
  required_version = ">= 1.7.0"

  # State remoto: o local se perdeu ao formatar o computador. O bucket é
  # criado fora do Terraform (bootstrap) porque o state não pode morar
  # num recurso gerenciado por ele mesmo:
  #   gcloud storage buckets create gs://affable-alpha-506516-r7-tfstate \
  #     --location=us-central1 --uniform-bucket-level-access \
  #     --public-access-prevention
  #   gcloud storage buckets update gs://affable-alpha-506516-r7-tfstate --versioning
  backend "gcs" {
    bucket = "affable-alpha-506516-r7-tfstate"
    prefix = "terraform/state"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}