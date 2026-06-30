######################################################################
# Secret Manager — metadata only.
#
# Terraform owns the secret containers and the per-secret IAM binding
# for the runtime SA. Secret VERSIONS (the actual values) are added
# out-of-band (e.g. `gcloud secrets versions add`). Never put secret
# values in Terraform.
#
# Replicas are user-managed in the workload region for latency and
# data residency.
######################################################################

resource "google_secret_manager_secret" "this" {
  for_each = toset(var.secret_names)

  project   = var.project_id
  secret_id = each.value

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

######################################################################
# Per-secret IAM — runtime SA gets secretAccessor on each secret,
# scoped to the resource (never project-wide).
######################################################################

resource "google_secret_manager_secret_iam_member" "runtime_accessor" {
  for_each = google_secret_manager_secret.this

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.runtime_sa_email}"
}
