output "runtime_sa_email" {
  description = "Email of the runtime service account."
  value       = google_service_account.runtime.email
}

output "runtime_sa_name" {
  description = "Fully qualified name of the runtime service account (projects/.../serviceAccounts/...)."
  value       = google_service_account.runtime.name
}

output "cicd_sa_email" {
  description = "Email of the CI/CD service account."
  value       = google_service_account.cicd.email
}

output "cicd_sa_name" {
  description = "Fully qualified name of the CI/CD service account (projects/.../serviceAccounts/...)."
  value       = google_service_account.cicd.name
}
