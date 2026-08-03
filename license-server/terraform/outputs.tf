output "project_id" {
  description = "GCP project used"
  value       = var.project_id
}

output "firestore_database" {
  description = "Firestore database name"
  value       = google_firestore_database.default.name
}

output "functions_service_account" {
  description = "Service account email for Cloud Functions"
  value       = google_service_account.functions_sa.email
}

output "jwt_secret_name" {
  description = "Secret Manager resource name for JWT private key"
  value       = google_secret_manager_secret.jwt_private_key.name
}

output "admin_key_secret_name" {
  description = "Secret Manager resource name for admin API key"
  value       = google_secret_manager_secret.admin_api_key.name
}
