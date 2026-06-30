######################################################################
# Generic, reusable Cloud Run v2 service.
#
# Owns the full revision template (image, SA, scaling, Direct VPC
# Egress, env, secret env, probes). The container image is the one
# attribute Terraform does NOT fight CI on — Cloud Build rolls new
# image SHAs on every push, so template[0].containers[0].image is the
# single accepted ignore_changes entry.
######################################################################

resource "google_cloud_run_v2_service" "this" {
  project  = var.project_id
  location = var.region
  name     = var.service_name
  ingress  = var.ingress

  deletion_protection = false

  template {
    service_account = var.service_account
    timeout         = "${var.timeout_seconds}s"

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    vpc_access {
      egress = var.vpc_egress
      network_interfaces {
        subnetwork = var.egress_subnet_id
      }
    }

    containers {
      image   = var.image
      command = var.command

      ports {
        container_port = var.port
      }

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        cpu_idle          = var.cpu_idle
        startup_cpu_boost = true
      }

      dynamic "env" {
        for_each = var.env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value.secret
              version = env.value.version
            }
          }
        }
      }

      dynamic "startup_probe" {
        for_each = var.startup_probe_path == "" ? [] : [1]
        content {
          initial_delay_seconds = 10
          timeout_seconds       = 5
          period_seconds        = 10
          failure_threshold     = 6
          http_get {
            path = var.startup_probe_path
            port = var.port
          }
        }
      }

      dynamic "liveness_probe" {
        for_each = var.liveness_probe_path == "" ? [] : [1]
        content {
          initial_delay_seconds = 30
          timeout_seconds       = 5
          period_seconds        = 30
          failure_threshold     = 3
          http_get {
            path = var.liveness_probe_path
            port = var.port
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      # Cloud Build rolls new images on every push — Terraform must not
      # fight CI on the image SHA.
      template[0].containers[0].image,
    ]
  }
}

######################################################################
# Public invoker binding — only when allow_unauthenticated is true.
######################################################################

resource "google_cloud_run_v2_service_iam_member" "public" {
  count = var.allow_unauthenticated ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
