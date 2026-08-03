terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Enable required GCP APIs ──────────────────────────────────
locals {
  apis = [
    "firebase.googleapis.com",
    "firestore.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each = toset(local.apis)

  service            = each.value
  disable_on_destroy = false
}

# ── Firestore database ────────────────────────────────────────
resource "google_firestore_database" "default" {
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.apis]
}

# ── Secret Manager: JWT private key ───────────────────────────
resource "google_secret_manager_secret" "jwt_private_key" {
  secret_id = "jwt-private-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# ── Secret Manager: Admin API key ─────────────────────────────
resource "google_secret_manager_secret" "admin_api_key" {
  secret_id = "admin-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# ── Service account for Cloud Functions ───────────────────────
resource "google_service_account" "functions_sa" {
  account_id   = "license-functions"
  display_name = "License Server Cloud Functions"
}

# Allow functions to read secrets
resource "google_secret_manager_secret_iam_member" "jwt_key_access" {
  secret_id = google_secret_manager_secret.jwt_private_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.functions_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "admin_key_access" {
  secret_id = google_secret_manager_secret.admin_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.functions_sa.email}"
}

# Allow functions SA to read/write Firestore
resource "google_project_iam_member" "firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.functions_sa.email}"
}
