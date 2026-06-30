######################################################################
# Artifact Registry — Docker repository for application images.
# Cleanup policy keeps the N most recent versions and deletes untagged
# images older than the configured age.
######################################################################

resource "google_artifact_registry_repository" "this" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repository_id
  description   = var.description
  format        = "DOCKER"

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "keep-recent-versions"
    action = "KEEP"
    most_recent_versions {
      keep_count = var.keep_recent_count
    }
  }

  cleanup_policies {
    id     = "delete-old-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "${var.delete_untagged_older_than_days * 24 * 60 * 60}s"
    }
  }
}
