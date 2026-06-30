######################################################################
# Cloud Build GitHub push trigger.
#
# Fires on pushes to the configured branch and runs the build defined
# by the repo's cloudbuild.yaml. Requires the GitHub repository to be
# connected to Cloud Build (1st-gen GitHub App connection) beforehand.
######################################################################

resource "google_cloudbuild_trigger" "this" {
  project         = var.project_id
  location        = var.region
  name            = var.trigger_name
  filename        = var.build_config_filename
  service_account = var.service_account
  substitutions   = var.substitutions

  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = var.branch_regex
    }
  }
}
