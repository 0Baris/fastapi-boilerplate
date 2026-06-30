######################################################################
# Cloud Run v2 Job — e.g. database migrations.
#
# Same connectivity model as the services: runs as the runtime SA with
# Direct VPC Egress so it can reach private Postgres / Redis. The image
# SHA is rewritten by Cloud Build per push, so it is the one accepted
# ignore_changes entry.
######################################################################

resource "google_cloud_run_v2_job" "this" {
  project  = var.project_id
  location = var.region
  name     = var.job_name

  deletion_protection = false

  template {
    parallelism = 1
    task_count  = 1

    template {
      service_account = var.service_account
      timeout         = "${var.task_timeout_seconds}s"
      max_retries     = var.max_retries

      vpc_access {
        egress = var.vpc_egress
        network_interfaces {
          subnetwork = var.egress_subnet_id
        }
      }

      containers {
        image   = var.image
        command = var.command

        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
          }
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
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image,
    ]
  }
}
