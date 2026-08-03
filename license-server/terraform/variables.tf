variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Functions"
  type        = string
  default     = "europe-west1"
}

variable "firestore_location" {
  description = "Firestore location (multi-region or single)"
  type        = string
  default     = "eur3"
}
