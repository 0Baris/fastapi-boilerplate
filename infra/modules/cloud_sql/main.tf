######################################################################
# Cloud SQL for PostgreSQL — private IP only (no public IPv4), reached
# over Private Service Access. Created fresh (greenfield); the instance
# depends on the PSA service networking connection being established.
######################################################################

resource "google_sql_database_instance" "this" {
  name                = var.instance_name
  project             = var.project_id
  region              = var.region
  database_version    = var.database_version
  deletion_protection = var.deletion_protection

  settings {
    tier              = var.tier
    edition           = var.edition
    disk_size         = var.disk_size
    disk_type         = var.disk_type
    availability_type = var.availability_type

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.vpc_self_link
      ssl_mode        = var.ssl_mode
    }
  }
}

######################################################################
# Application database.
######################################################################

resource "google_sql_database" "app" {
  name     = var.database_name
  project  = var.project_id
  instance = google_sql_database_instance.this.name
}

######################################################################
# Application database user.
######################################################################

resource "google_sql_user" "app" {
  name     = var.db_user
  project  = var.project_id
  instance = google_sql_database_instance.this.name
  password = var.db_password
}
