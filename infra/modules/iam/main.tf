######################################################################
# Workload identities.
#   runtime : used by Cloud Run services + the migrate Job.
#   cicd    : used by Cloud Build to push images, deploy revisions,
#             and impersonate the runtime SA.
######################################################################

resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = var.runtime_sa_account_id
  display_name = var.runtime_sa_display_name
}

resource "google_service_account" "cicd" {
  project      = var.project_id
  account_id   = var.cicd_sa_account_id
  display_name = var.cicd_sa_display_name
}

######################################################################
# Runtime SA — project-level roles.
#   cloudsql.client : open connections to the Cloud SQL instance.
#   logging.logWriter / monitoring.metricWriter : Cloud Run revisions
#     need these once the default compute SA is no longer used.
######################################################################

locals {
  runtime_project_roles = [
    "roles/cloudsql.client",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ]

  # CI/CD project-level roles. secretAccessor for the runtime SA is
  # bound per-secret in the secrets module, not here.
  cicd_project_roles = [
    "roles/run.developer",
    "roles/artifactregistry.writer",
    "roles/cloudsql.client",
  ]
}

resource "google_project_iam_member" "runtime_project" {
  for_each = toset(local.runtime_project_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

######################################################################
# Runtime SA — secretAccessor at the project level so it can read
# Secret Manager secrets. (The secrets module also binds this per
# secret; the project-level grant covers any secret created later.)
######################################################################

resource "google_project_iam_member" "runtime_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

######################################################################
# Runtime SA — GCS bucket-scoped object access (only when buckets are
# supplied). objectUser covers read/write/delete on objects without
# granting bucket-admin or project-level storage roles.
######################################################################

resource "google_storage_bucket_iam_member" "runtime_buckets" {
  for_each = toset(var.runtime_bucket_names)

  bucket = each.value
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

######################################################################
# CI/CD SA — project-level roles.
######################################################################

resource "google_project_iam_member" "cicd_project" {
  for_each = toset(local.cicd_project_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cicd.email}"
}

######################################################################
# CI/CD SA — scoped impersonation of the runtime SA.
# Required so Cloud Run deploys can set --service-account=<runtime>.
# Granted on the runtime SA resource only (NOT project-wide).
######################################################################

resource "google_service_account_iam_member" "cicd_impersonates_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.cicd.email}"
}
