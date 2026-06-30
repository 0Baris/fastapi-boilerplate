######################################################################
# Memorystore for Redis — reached privately via Private Service Access.
# AUTH and transit encryption are on by default (greenfield).
######################################################################

resource "google_redis_instance" "this" {
  name           = var.instance_name
  project        = var.project_id
  region         = var.region
  tier           = var.tier
  memory_size_gb = var.memory_size_gb
  redis_version  = var.redis_version

  authorized_network = var.authorized_network
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  auth_enabled            = var.auth_enabled
  transit_encryption_mode = var.transit_encryption_mode
}
